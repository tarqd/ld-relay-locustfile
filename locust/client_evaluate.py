import six
import sys

from ldclient.util import stringify_attrs, log
from ldclient.versioned_data_kind import FEATURES, SEGMENTS

from ldclient.flag import __USER_ATTRS_TO_STRINGIFY_FOR_EVALUATION__, EvalResult, EvaluationDetail



def evaluate(flag, store, event_factory):
    value = flag.get('value')
    version = flag.get('version')
    variation_index = flag.get('variation')
    reason = flag.get('reason')
    detail = EvaluationDetail(value, variation_index, reason)
    # TODO: generate evaluation event
    return EvalResult(detail = detail, events = None)
