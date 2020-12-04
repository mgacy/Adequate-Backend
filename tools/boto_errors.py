import boto3
from botocore.exceptions import ClientError

STATUS_CODES = {
    # Client Error.
    400: 'bad_request',
    401: 'unauthorized',
    402: 'payment_required',
    403: 'forbidden',
    404: 'not_found',
    405: 'method_not_allowed',
    406: 'not_acceptable',
    407: 'proxy_authentication_required',
    408: 'request_timeout',
    409: 'conflict',
    410: 'gone',
    411: 'length_required',
    412: 'precondition_failed',
    413: 'request_entity_too_large',
    414: 'request_uri_too_large',
    415: 'unsupported_media_type',
    416: 'requested_range_not_satisfiable',
    417: 'expectation_failed',
    418: 'im_a_teapot',
    421: 'misdirected_request',
    422: 'unprocessable_entity',
    423: 'locked',
    424: 'failed_dependency',
    425: 'unordered_collection',
    426: 'upgrade_required',
    428: 'precondition_required',
    429: 'too_many_requests',
    431: 'header_fields_too_large',
    444: 'no_response',
    449: 'retry_with',
    450: 'blocked_by_windows_parental_controls',
    451: 'unavailable_for_legal_reasons',
    499: 'client_closed_request',

    # Server Error.
    500: 'internal_server_error',
    501: 'not_implemented',
    502: 'bad_gateway',
    503: 'service_unavailable',
    504: 'gateway_timeout',
    505: 'http_version_not_supported',
    506: 'variant_also_negotiates',
    507: 'insufficient_storage',
    509: 'bandwidth_limit_exceeded',
    510: 'not_extended',
    511: 'network_authentication_required'
}


class ResponseStatusError(Exception):
    """A boto3 request was not successful.

    Attributes
    ----------
    msg : str
        Error message
    response : dict
        Request response
    """

    def __init__(self, status_code, response):
        # TODO: map different errors (400 - 499 / 500 - 599)?
        self.msg = f'Error: {status_code}'
        # TODO: extract `response['ResponseMetadata']`?
        self.response = response


def raise_for_status(response):
    """Raises `ResponseStatusError` if boto3 request was not successful.

    Parameters
    ----------
    response : dict
        Response from boto3 request

    Raises
    ------
    ResponseStatusError
        Response status code was not 200
    """
    status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    # TODO: allow other 200 codes as well?
    if status_code != 200:
        # msg = ''
        # if 400 <= status_code < 500:
        #     msg = f'{status_code} Client Error: {STATUS_CODES[status_code]}'
        # elif 500 <= status_code < 600:
        #     msg = f'{status_code} Server Error: {STATUS_CODES[status_code]}'

        # raise ResponseStatusError(msg, response)
        raise ResponseStatusError(status_code, response)
