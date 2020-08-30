"""
Meh API Services.

v 0.2
"""

from datetime import datetime as dt
import re
# import requests
from .deal import get_launch_status

# endpoint = 'https://api.meh.com/1/current.json'


# def get(api_key):
#     """Return current deal from meh.com API with additional processing.

#     Parameters
#     ----------
#     api_key : string
#         API key for meh.com

#     Returns
#     -------
#     dict
#         Response

#     Raises
#     ------
#     requests.exceptions.RequestException
#         Description
#     """
#     params = {'apikey': api_key}
#     r = requests.get(meh_endpoint, params=params)
#     r.raise_for_status()
#     return _parse_response(r.json())


def _fix_empty_array(item, key, nullable=True):
    """Return `item`, replacing an empty list for key `key` with an
    appropriate value for a GraphQL mutation.

    Values for keys other than `key` will be unchanges.

    Process `item` to accommodate GraphQL schemas with declarations of the
    following type:

    Declaration where `nullable` is `True`:

        type item {
            key: [<SomeType>]
            ...
        }

    Declaration where `nullable` is `False`:

        type item {
            key: [<SomeType>!]
            ...
        }

    Examples:

        r = _fix_empty_array({'attributes': []}, 'attributes', nullable=True)
        # {'attributes': [None]}

        r = _fix_empty_array({'attributes': []}, 'attributes', nullable=False)
        # {'attributes': None}

    Parameters
    ----------
    item : dict
        [description]
    key : str
        Key for value that will be processed
    nullable : bool, optional
        If `False`, will add `key` to `item` if it does not already have it

    Returns
    -------
    dict
        Updated `item`
    """
    def_value = [None] if nullable else None
    if item.get(key, []) == []:
        item[key] = def_value
    return item


def _parse_creation_date(response):
    """Parse or generate creation date from response.

    Parameters
    ----------
    response : dict
        Response from meh.com API

    Returns
    -------
    str
        Creation date for deal
    """
    created_at = response.get('deal', {}).get('topic', {}).get('createdAt')
    if created_at is None:
        created_at = response.get('poll', {}).get('startDate')

    if created_at is None:
        print('Fall-back created_at method')
        # https://stackoverflow.com/a/52836471/4472195
        # TODO: handle timezone?
        now = dt.utcnow()
        created_at = (now.strftime('%Y-%m-%dT%H:%M:%S')
                      + now.strftime('.%f')[:4] + 'Z')
    return created_at


def _parse_model_numbers(deal):
    """Parse model numbers from response.

    Parameters
    ----------
    deal : dict
        Description

    Returns
    -------
    list
        List of model numbers
    """
    specs = deal.get('specifications')
    if specs is None:
        return  # TODO: return `[]`?`
    # TODO: move `search_pattern` out into class property?
    line_search_pattern = re.compile(r"""
        ^\s*-\sModel:\s
        (?P<model>
            [\d,a-z,A-Z,\-,\,,\s,\\,/]*
        )
        \s*
        $
        """, (re.X | re.M))
    model_numbers = line_search_pattern.findall(specs)

    # Split commas
    lists = [string.split(',') for string in model_numbers]
    # Strip unwanted characters
    # return [item.strip() for sublist in lists for item in sublist]
    return list(filter(None, [item.strip() for sublist in lists
                for item in sublist]))


# Rename `process_response`?
def _parse_response(response):
    """Docstring.

    Extracts `deal` from server response and adds the following fields:

    dealID : str
        `id` of deal (since `Deal.id` will be `current_deal` in AppSync)
    createdAt : str
        Creation date extracted from `topic`, `poll`, or time fetched
    modelNumbers : [str]
        Array of model numbers extracted from `specifications`
    launchStatus : LaunchStatus
        Status of launch

    Mutates the following fields:

    items : list[dict]

    Parameters
    ----------
    response : dict
        Server response from Meh API

    Returns
    -------
    dict
        Updated deal dict
    """
    deal = response['deal']
    deal['dealID'] = deal['id']

    # Set .createdAt
    created_at = _parse_creation_date(response)
    deal.update(createdAt=created_at)

    # Extract model numbers
    model_numbers = _parse_model_numbers(deal)
    # FIXME: handle empty `model_numbers`
    deal.update(modelNumbers=model_numbers)

    # Set .launchStatus
    launch_status = get_launch_status(deal)
    deal.update(launchStatus=launch_status.name)

    # Convert floats (sometimes) to ints
    # for item in deal.get('items', []):
    #     curr_price = item.get('price', 0)
    #     item['price'] = curr_price * 100

    # Handle error when `Item.attributes` is `[]`
    deal['items'] = [_fix_empty_array(i, 'attributes', nullable=True)
                     for i in deal.get('items', [])]

    return deal
