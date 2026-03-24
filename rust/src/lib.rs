#![forbid(unsafe_code)]

use std::cmp::Ordering;
use std::sync::{Arc, Mutex};

use pyo3::exceptions::{PyIndexError, PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyBool, PyBytes, PyDateTime, PyDict, PyList, PyModule, PyString, PyTuple};
use qs_rust::{
    Charset, DecodeOptions, Duplicates, EncodeFilter, EncodeOptions, EncodeToken,
    EncodeTokenEncoder, FilterResult, Format, FunctionFilter, ListFormat, Object, Sorter,
    TemporalSerializer, TemporalValue, Value, decode_pairs as qs_decode_pairs, encode as qs_encode,
};

#[pyfunction]
fn encode(
    _py: Python<'_>,
    value: &Bound<'_, PyAny>,
    config: &Bound<'_, PyDict>,
    callbacks: Option<Py<PyAny>>,
) -> PyResult<String> {
    let rust_value = py_to_encode_value(value)?;
    let callback_state = callbacks.map(NativeEncodeCallbacks::new);
    let options = parse_encode_options(config, callback_state.clone())?;
    let result = qs_encode(&rust_value, &options);

    if let Some(state) = callback_state
        && let Some(err) = state.take_error()
    {
        return Err(err);
    }

    result.map_err(map_encode_error)
}

#[pyfunction]
fn decode_pairs(
    py: Python<'_>,
    pairs: Vec<(String, Py<PyAny>)>,
    config: &Bound<'_, PyDict>,
) -> PyResult<Py<PyAny>> {
    let options = parse_decode_options(config)?;
    let rust_pairs = pairs
        .into_iter()
        .map(|(key, value)| Ok((key, py_to_decode_value(value.bind(py))?)))
        .collect::<PyResult<Vec<_>>>()?;

    let decoded = qs_decode_pairs(rust_pairs, &options).map_err(|err| map_decode_error_with_config(err, config))?;
    object_to_py(py, &decoded)
}

#[pymodule(gil_used = false)]
fn _qs_rust(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(encode, module)?)?;
    module.add_function(wrap_pyfunction!(decode_pairs, module)?)?;
    Ok(())
}

#[derive(Clone)]
struct NativeEncodeCallbacks {
    bridge: Arc<Py<PyAny>>,
    error: Arc<Mutex<Option<PyErr>>>,
}

impl NativeEncodeCallbacks {
    fn new(bridge: Py<PyAny>) -> Self {
        Self {
            bridge: Arc::new(bridge),
            error: Arc::new(Mutex::new(None)),
        }
    }

    fn record_error(&self, err: PyErr) {
        let mut slot = self.error.lock().expect("encode callback error mutex poisoned");
        if slot.is_none() {
            *slot = Some(err);
        }
    }

    fn take_error(&self) -> Option<PyErr> {
        self.error
            .lock()
            .expect("encode callback error mutex poisoned")
            .take()
    }

    fn invoke_filter(&self, prefix: &str, value: &Value) -> FilterResult {
        Python::attach(|py| {
            let py_value = match value_to_py(py, value) {
                Ok(value) => value,
                Err(err) => {
                    self.record_error(err);
                    return FilterResult::Omit;
                }
            };

            let result = self
                .bridge
                .as_ref()
                .bind(py)
                .call_method1("apply_filter", (prefix, py_value));
            let (action, payload): (String, Py<PyAny>) = match result.and_then(|value| value.extract()) {
                Ok(result) => result,
                Err(err) => {
                    self.record_error(err);
                    return FilterResult::Omit;
                }
            };

            match action.as_str() {
                "keep" => FilterResult::Keep,
                "omit" => FilterResult::Omit,
                "replace" => match py_to_encode_value(payload.bind(py)) {
                    Ok(value) => FilterResult::Replace(value),
                    Err(err) => {
                        self.record_error(err);
                        FilterResult::Omit
                    }
                },
                other => {
                    self.record_error(PyRuntimeError::new_err(format!(
                        "unsupported encode filter action {:?}",
                        other
                    )));
                    FilterResult::Omit
                }
            }
        })
    }

    fn invoke_encoder(&self, token: EncodeToken<'_>) -> String {
        Python::attach(|py| {
            let py_token = match encode_token_to_py(py, token) {
                Ok(value) => value,
                Err(err) => {
                    self.record_error(err);
                    return String::new();
                }
            };

            let result = self
                .bridge
                .as_ref()
                .bind(py)
                .call_method1("encode_token", (py_token,));
            match result.and_then(|value| {
                value
                    .extract::<String>()
                    .or_else(|_| value.str().map(|text| text.to_string_lossy().into_owned()))
            }) {
                Ok(encoded) => encoded,
                Err(err) => {
                    self.record_error(err);
                    String::new()
                }
            }
        })
    }

    fn invoke_sorter(&self, left: &str, right: &str) -> Ordering {
        Python::attach(|py| {
            let result = self
                .bridge
                .as_ref()
                .bind(py)
                .call_method1("compare", (left, right))
                .and_then(|value| value.extract::<i64>());
            match result {
                Ok(ordering) if ordering < 0 => Ordering::Less,
                Ok(ordering) if ordering > 0 => Ordering::Greater,
                Ok(_) => Ordering::Equal,
                Err(err) => {
                    self.record_error(err);
                    Ordering::Equal
                }
            }
        })
    }

    fn invoke_temporal(&self, value: &TemporalValue) -> Option<String> {
        Python::attach(|py| {
            let py_value = match temporal_to_py(py, value) {
                Ok(value) => value,
                Err(err) => {
                    self.record_error(err);
                    return None;
                }
            };

            let result = self
                .bridge
                .as_ref()
                .bind(py)
                .call_method1("serialize_temporal", (py_value,));
            match result.and_then(|value| value.extract::<Option<String>>()) {
                Ok(serialized) => serialized,
                Err(err) => {
                    self.record_error(err);
                    None
                }
            }
        })
    }
}

fn parse_encode_options(
    config: &Bound<'_, PyDict>,
    callbacks: Option<NativeEncodeCallbacks>,
) -> PyResult<EncodeOptions> {
    let mut options = EncodeOptions::new()
        .with_encode(required_bool(config, "encode")?)
        .with_delimiter(required_string(config, "delimiter")?)
        .with_list_format(parse_list_format(config)?)
        .with_charset(parse_charset(config)?)
        .with_format(parse_format(config)?)
        .with_charset_sentinel(required_bool(config, "charset_sentinel")?)
        .with_allow_empty_lists(required_bool(config, "allow_empty_lists")?)
        .with_strict_null_handling(required_bool(config, "strict_null_handling")?)
        .with_skip_nulls(required_bool(config, "skip_nulls")?)
        .with_comma_round_trip(required_bool(config, "comma_round_trip")?)
        .with_comma_compact_nulls(required_bool(config, "comma_compact_nulls")?)
        .with_encode_values_only(required_bool(config, "encode_values_only")?)
        .with_add_query_prefix(required_bool(config, "add_query_prefix")?)
        .with_allow_dots(required_bool(config, "allow_dots")?)
        .with_encode_dot_in_keys(required_bool(config, "encode_dot_in_keys")?)
        .with_max_depth(optional_usize(config, "max_depth")?);

    let whitelist_keys = optional_string_list(config, "whitelist_keys")?;
    let whitelist_indices = optional_usize_list(config, "whitelist_indices")?;
    if !whitelist_keys.is_empty() || !whitelist_indices.is_empty() {
        let selectors = whitelist_keys
            .into_iter()
            .map(qs_rust::WhitelistSelector::Key)
            .chain(
                whitelist_indices
                    .into_iter()
                    .map(qs_rust::WhitelistSelector::Index),
            )
            .collect();
        options = options.with_whitelist(Some(selectors));
    }

    if let Some(callbacks) = callbacks {
        if required_bool(config, "has_function_filter")? {
            let filter_callbacks = callbacks.clone();
            options = options.with_filter(Some(EncodeFilter::Function(FunctionFilter::new(
                move |prefix, value| filter_callbacks.invoke_filter(prefix, value),
            ))));
        }

        if required_bool(config, "has_sorter")? {
            let sorter_callbacks = callbacks.clone();
            options = options.with_sorter(Some(Sorter::new(move |left, right| {
                sorter_callbacks.invoke_sorter(left, right)
            })));
        }

        if required_bool(config, "has_encoder")? {
            let encoder_callbacks = callbacks.clone();
            options = options.with_encoder(Some(EncodeTokenEncoder::new(move |token, _, _| {
                encoder_callbacks.invoke_encoder(token)
            })));
        }

        let temporal_callbacks = callbacks.clone();
        options = options.with_temporal_serializer(Some(TemporalSerializer::new(move |value| {
            temporal_callbacks.invoke_temporal(value)
        })));
    }

    Ok(options)
}

fn parse_decode_options(config: &Bound<'_, PyDict>) -> PyResult<DecodeOptions> {
    Ok(DecodeOptions::new()
        .with_allow_dots(required_bool(config, "allow_dots")?)
        .with_decode_dot_in_keys(required_bool(config, "decode_dot_in_keys")?)
        .with_allow_empty_lists(required_bool(config, "allow_empty_lists")?)
        .with_list_limit(required_usize(config, "list_limit")?)
        .with_depth(required_usize(config, "depth")?)
        .with_duplicates(parse_duplicates(config)?)
        .with_parse_lists(required_bool(config, "parse_lists")?)
        .with_strict_depth(required_bool(config, "strict_depth")?)
        .with_strict_null_handling(required_bool(config, "strict_null_handling")?)
        .with_throw_on_limit_exceeded(required_bool(config, "raise_on_limit_exceeded")?)
        .with_parameter_limit(required_usize(config, "parameter_limit")?))
}

fn py_to_encode_value(value: &Bound<'_, PyAny>) -> PyResult<Value> {
    if value.is_none() {
        return Ok(Value::Null);
    }
    if let Ok(boolean) = value.extract::<bool>() {
        return Ok(Value::Bool(boolean));
    }
    if let Ok(bytes) = value.cast::<PyBytes>() {
        return Ok(Value::Bytes(bytes.as_bytes().to_vec()));
    }
    if let Ok(datetime) = value.cast::<PyDateTime>() {
        let iso = datetime.call_method0("isoformat")?.extract::<String>()?;
        let temporal = TemporalValue::parse_iso8601(&iso)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        return Ok(Value::Temporal(temporal));
    }
    if let Ok(text) = value.cast::<PyString>() {
        return Ok(Value::String(text.to_string_lossy().into_owned()));
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let mut object = Object::new();
        for (key, item) in dict.iter() {
            object.insert(key.extract::<String>()?, py_to_encode_value(&item)?);
        }
        return Ok(Value::Object(object));
    }
    if let Ok(list) = value.cast::<PyList>() {
        let items = list
            .iter()
            .map(|item| py_to_encode_value(&item))
            .collect::<PyResult<Vec<_>>>()?;
        return Ok(Value::Array(items));
    }
    if let Ok(tuple) = value.cast::<PyTuple>() {
        let items = tuple
            .iter()
            .map(|item| py_to_encode_value(&item))
            .collect::<PyResult<Vec<_>>>()?;
        return Ok(Value::Array(items));
    }
    if let Ok(integer) = value.extract::<i64>() {
        return Ok(Value::I64(integer));
    }
    if let Ok(integer) = value.extract::<u64>() {
        return Ok(Value::U64(integer));
    }
    if let Ok(float) = value.extract::<f64>() {
        return Ok(Value::F64(float));
    }

    Err(PyTypeError::new_err(format!(
        "unsupported native encode value type: {}",
        value.get_type().name()?
    )))
}

fn py_to_decode_value(value: &Bound<'_, PyAny>) -> PyResult<Value> {
    if value.is_none() {
        return Ok(Value::Null);
    }
    if let Ok(boolean) = value.extract::<bool>() {
        return Ok(Value::Bool(boolean));
    }
    if let Ok(bytes) = value.cast::<PyBytes>() {
        return Ok(Value::Bytes(bytes.as_bytes().to_vec()));
    }
    if let Ok(datetime) = value.cast::<PyDateTime>() {
        let iso = datetime.call_method0("isoformat")?.extract::<String>()?;
        let temporal = TemporalValue::parse_iso8601(&iso)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        return Ok(Value::Temporal(temporal));
    }
    if let Ok(text) = value.cast::<PyString>() {
        return Ok(Value::String(text.to_string_lossy().into_owned()));
    }
    if let Ok(integer) = value.extract::<i64>() {
        return Ok(Value::I64(integer));
    }
    if let Ok(integer) = value.extract::<u64>() {
        return Ok(Value::U64(integer));
    }
    if let Ok(float) = value.extract::<f64>() {
        return Ok(Value::F64(float));
    }

    Err(PyTypeError::new_err(format!(
        "unsupported native decode pair value type: {}",
        value.get_type().name()?
    )))
}

fn encode_token_to_py(py: Python<'_>, token: EncodeToken<'_>) -> PyResult<Py<PyAny>> {
    match token {
        EncodeToken::Key(key) => Ok(PyString::new(py, key).into_any().unbind()),
        EncodeToken::Value(value) => value_to_py(py, value),
        EncodeToken::TextValue(text) => Ok(PyString::new(py, text).into_any().unbind()),
    }
}

fn object_to_py(py: Python<'_>, object: &Object) -> PyResult<Py<PyAny>> {
    let dict = PyDict::new(py);
    for (key, value) in object {
        dict.set_item(key, value_to_py(py, value)?)?;
    }
    Ok(dict.into_any().unbind())
}

fn value_to_py(py: Python<'_>, value: &Value) -> PyResult<Py<PyAny>> {
    match value {
        Value::Null => Ok(py.None()),
        Value::Bool(value) => Ok(PyBool::new(py, *value).to_owned().into_any().unbind()),
        Value::I64(value) => Ok((*value).into_pyobject(py)?.into_any().unbind()),
        Value::U64(value) => Ok((*value).into_pyobject(py)?.into_any().unbind()),
        Value::F64(value) => Ok((*value).into_pyobject(py)?.into_any().unbind()),
        Value::String(value) => Ok(value.into_pyobject(py)?.into_any().unbind()),
        Value::Bytes(value) => Ok(PyBytes::new(py, value).into_any().unbind()),
        Value::Temporal(value) => temporal_to_py(py, value),
        Value::Array(items) => {
            let list = PyList::empty(py);
            for item in items {
                list.append(value_to_py(py, item)?)?;
            }
            Ok(list.into_any().unbind())
        }
        Value::Object(entries) => object_to_py(py, entries),
    }
}

fn temporal_to_py(py: Python<'_>, value: &TemporalValue) -> PyResult<Py<PyAny>> {
    let datetime_module = py.import("datetime")?;
    let datetime_type = datetime_module.getattr("datetime")?;
    let parsed = datetime_type.call_method1("fromisoformat", (value.to_string(),))?;
    Ok(parsed.into_any().unbind())
}

fn map_encode_error(err: qs_rust::EncodeError) -> PyErr {
    match err {
        qs_rust::EncodeError::DepthExceeded { .. } => {
            PyValueError::new_err("Maximum encoding depth exceeded")
        }
        other => PyValueError::new_err(other.to_string()),
    }
}

fn map_decode_error(err: qs_rust::DecodeError) -> PyErr {
    match err {
        qs_rust::DecodeError::ListLimitExceeded { limit } => PyValueError::new_err(format!(
            "List limit exceeded: Only {limit} element{} allowed in a list.",
            if limit == 1 { "" } else { "s" }
        )),
        qs_rust::DecodeError::DepthExceeded { depth } => {
            PyIndexError::new_err(format!(
                "Input depth exceeded depth option of {depth} and strict_depth is True"
            ))
        }
        other => PyValueError::new_err(other.to_string()),
    }
}

fn map_decode_error_with_config(err: qs_rust::DecodeError, config: &Bound<'_, PyDict>) -> PyErr {
    match err {
        qs_rust::DecodeError::ListLimitExceeded { limit } => {
            let display_limit = optional_usize(config, "original_list_limit")
                .ok()
                .flatten()
                .unwrap_or(limit);
            PyValueError::new_err(format!(
                "List limit exceeded: Only {display_limit} element{} allowed in a list.",
                if display_limit == 1 { "" } else { "s" }
            ))
        }
        other => map_decode_error(other),
    }
}

fn required_string(config: &Bound<'_, PyDict>, key: &str) -> PyResult<String> {
    config
        .get_item(key)?
        .ok_or_else(|| PyRuntimeError::new_err(format!("missing native config key {:?}", key)))?
        .extract::<String>()
}

fn required_bool(config: &Bound<'_, PyDict>, key: &str) -> PyResult<bool> {
    config
        .get_item(key)?
        .ok_or_else(|| PyRuntimeError::new_err(format!("missing native config key {:?}", key)))?
        .extract::<bool>()
}

fn required_usize(config: &Bound<'_, PyDict>, key: &str) -> PyResult<usize> {
    config
        .get_item(key)?
        .ok_or_else(|| PyRuntimeError::new_err(format!("missing native config key {:?}", key)))?
        .extract::<usize>()
}

fn optional_usize(config: &Bound<'_, PyDict>, key: &str) -> PyResult<Option<usize>> {
    let Some(value) = config.get_item(key)? else {
        return Ok(None);
    };
    if value.is_none() {
        return Ok(None);
    }
    value.extract::<Option<usize>>()
}

fn optional_string_list(config: &Bound<'_, PyDict>, key: &str) -> PyResult<Vec<String>> {
    let Some(value) = config.get_item(key)? else {
        return Ok(Vec::new());
    };
    value.extract::<Vec<String>>()
}

fn optional_usize_list(config: &Bound<'_, PyDict>, key: &str) -> PyResult<Vec<usize>> {
    let Some(value) = config.get_item(key)? else {
        return Ok(Vec::new());
    };
    value.extract::<Vec<usize>>()
}

fn parse_list_format(config: &Bound<'_, PyDict>) -> PyResult<ListFormat> {
    match required_string(config, "list_format")?.as_str() {
        "INDICES" => Ok(ListFormat::Indices),
        "BRACKETS" => Ok(ListFormat::Brackets),
        "REPEAT" => Ok(ListFormat::Repeat),
        "COMMA" => Ok(ListFormat::Comma),
        other => Err(PyRuntimeError::new_err(format!(
            "unsupported list_format {:?}",
            other
        ))),
    }
}

fn parse_charset(config: &Bound<'_, PyDict>) -> PyResult<Charset> {
    match required_string(config, "charset")?.as_str() {
        "utf-8" => Ok(Charset::Utf8),
        "iso-8859-1" => Ok(Charset::Iso88591),
        other => Err(PyRuntimeError::new_err(format!(
            "unsupported charset {:?}",
            other
        ))),
    }
}

fn parse_format(config: &Bound<'_, PyDict>) -> PyResult<Format> {
    match required_string(config, "format")?.as_str() {
        "RFC3986" => Ok(Format::Rfc3986),
        "RFC1738" => Ok(Format::Rfc1738),
        other => Err(PyRuntimeError::new_err(format!(
            "unsupported format {:?}",
            other
        ))),
    }
}

fn parse_duplicates(config: &Bound<'_, PyDict>) -> PyResult<Duplicates> {
    match required_string(config, "duplicates")?.as_str() {
        "combine" => Ok(Duplicates::Combine),
        "first" => Ok(Duplicates::First),
        "last" => Ok(Duplicates::Last),
        other => Err(PyRuntimeError::new_err(format!(
            "unsupported duplicates mode {:?}",
            other
        ))),
    }
}
