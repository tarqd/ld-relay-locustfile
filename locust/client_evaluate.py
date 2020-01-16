import six
import sys

from ldclient.util import stringify_attrs, log
from ldclient.versioned_data_kind import FEATURES, SEGMENTS

from ldclient.flag import __USER_ATTRS_TO_STRINGIFY_FOR_EVALUATION__, EvalResult, EvaluationDetail



def evaluate(flag, user, store, event_factory):
    sanitized_user = stringify_attrs(user, __USER_ATTRS_TO_STRINGIFY_FOR_EVALUATION__)
    value = flag.get('value')
    version = flag.get('version')
    variation_index = flag.get('variation')
    reason = flag.get('reason')
    detail = EvaluationDetail(value, variation_index, reason)

    return EvalResult(detail = detail, events = None)
