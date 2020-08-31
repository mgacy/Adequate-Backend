"""
AppSync API Service.

v 0.1
"""

import json
# from boto3.session import Session as AWSSession
import requests
# from requests.exceptions import RequestException
from requests_aws4auth import AWS4Auth


# TODO: add base exception and subclass to wrap requests exceptions
# TODO: add separate exception for responses that are missing data
# TODO: maybe look at graphql-core.
class GraphQLError(Exception):
    """GraphQL error.

    https://spec.graphql.org/June2018/#sec-Errors

    Attributes
    ----------
    error_info : TYPE
        AppSync-specific attribute
    error_type : TYPE
        AppSync-specific attribute
    locations : dict
        Describes the beginning of an associated syntax element

        line : int
        column : int
    message : str
        Description of the error
    path : list
        Describes the path of the response field which experienced the error.
    """

    def __init__(self, message, locations, path, **kwargs):
        super().__init__(message)
        self.message = message
        self.locations = locations
        self.path = path
        # AppSync-specific attributes (not part of GraphQL spec)
        self.error_type = kwargs.get('errorType', None)
        self.error_info = kwargs.get('errorInfo', None)


# Use this to wrap requests.exceptions.RequestException / GraphQLError?
class AppSyncException(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.message = message
        self.errors = errors
        # TODO: add separate `details` attr?
        # TODO: add `error_type` property?


# Fragments on Deal for GraphQL selection sets
DEAL_FRAGMENTS = {
    'item': 'items { id attributes { key value } condition price photo } ',
    'launches': 'launches { soldOutAt } ',
    'purchaseQuantity': 'purchaseQuantity { maximumLimit minimumLimit } ',
    'story': 'story { title body } ',
    'theme': 'theme { accentColor backgroundColor backgroundImage foreground } ',  # noqa E501
    'topic': 'topic { id commentCount createdAt replyCount url voteCount } ',
    # Sets of fields
    'update': '_lastChangedAt _version _deleted ',
}


# TODO: create subclass for single operations and add parameter for operation
# field; add property to return `data.get(op_field, None)`
class GraphQLResponse(object):

    def __init__(self, json_body):
        # super(GraphQLResponse, self).__init__()  # ?

        # See: https://spec.graphql.org/June2018/#sec-Response
        self.errors = [GraphQLError(**e) for e in json_body.get('errors', [])]
        self.data = json_body.get('data', None)
        # self.extensions = json_body.get('extensions', None)

    # def __repr__(self):

    def get(self, field):
        """Convenience method to return value for `data[field]` or None.

        Parameters
        ----------
        field : str
            Field to return

        Returns
        -------
        dict
            Value for data[field]
        """
        return self.data.get(field, None)

    def raise_for_errors(self):
        """Raises AppSyncException if any errors occurred.

        Inspired by requests.Response.raise_for_status()

        Raises
        ------
        AppSyncException
            Response contained errors
        """
        # TODO: improve error descriptions; try to categorize different errors
        if self.errors:
            raise AppSyncException(message='There were GraphQL errors',
                                   errors=self.errors)
        if self.data is None:
            raise AppSyncException(message='Missing data')


# TODO: Make `GraphQLMixin` for general GraphQL functions'
# See requests.models for inspiration
class AppSync(object):

    ALLOWED_OPERATION_ARGS = [
        'mutation',
        'query'
    ]

    ALLOWED_MUTATION_ARGS = [
        'create',
        'delete',
        'update'
    ]

    # Default selection set
    def_selection_set = (
        'id title'
    )

    def __init__(self, url):
        self.url = url
        # self.aws = aws_session

    def auth(self, aws_session):
        # See:
        # https://stackoverflow.com/a/60311232
        # https://gist.github.com/bencord0/70f9de572f0e284c94b7bcbf918dc0eb
        credentials = aws_session.get_credentials().get_frozen_credentials()
        session = requests.Session()
        # Create a `requests` compatible auth object
        # This param constructs an object for use with STS temporary
        # credentials. The requests_aws4auth README notes that it does not
        # manage temporary credential timeouts and that if the temporary
        # credentials expire, they need to be re-generated and the AWS4Auth
        # object re-constructed with the new credentials.
        session.auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            aws_session.region_name,
            'appsync',
            session_token=credentials.token
        )
        session.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        self.session = session
        return session

    # -------------------------------------------------------------------------
    # Requests

    def get_deal(self, id):
        """Execute `getDeal` query using `id` and return result.

        Parameters
        ----------
        id : str
            Deal id

        Returns
        -------
        GraphQLResponse
            Response from API
        """
        # Query.getDeal(id: ID!): Deal
        op_name = 'GetDeal'  # TODO: this could be generalized in other method
        var_defs = '$id: ID!'
        args = 'id: $id'

        # TODO: make this class property so we can use as default selection_set
        # in `create_deal()`?
        # if selection_set is None:
        selection_set = (
            'id dealID title features specifications url '
            'createdAt '
            # 'updatedAt '  # ?
            'modelNumbers photos launchStatus '
            'launches { soldOutAt } '
            'soldOutAt '
            '_version '
            'items { id attributes { key value } condition price photo } '
            'story { title body } '
            'topic { id commentCount createdAt replyCount url voteCount } '
            'theme { accentColor backgroundColor backgroundImage foreground } '  # noqa E501
            'purchaseQuantity { maximumLimit minimumLimit } '
        )

        query = self._make_query('query', op_name, var_defs, 'getDeal', args,
                                 selection_set)
        body = {'query': query, 'variables': {'id': id}}
        return self.execute(body)

    def create_deal(self, deal_input, selection_set=None):
        """Execute `createDeal` mutation and return result.

        Parameters
        ----------
        deal_input : str
            Description
        selection_set : str, optional
            Description

        Returns
        -------
        GraphQLResponse
            Response from API

        Raises
        ------
        ValueError
            Description
        """
        if selection_set is None:
            selection_set = self.def_selection_set

        body = self._make_mutation('Deal', 'create', deal_input,
                                   selection_set)
        return self.execute(body)

    def update_deal(self, deal_input, selection_set=None):
        """Execute `updateDeal` mutation and return result.

        Parameters
        ----------
        deal_input : TYPE
            Description
        selection_set : str, optional
            Description

        Returns
        -------
        GraphQLResponse
            Response from API

        Raises
        ------
        ValueError
            Description
        """
        if selection_set is None:
            selection_set = self.def_selection_set

        body = self._make_mutation('Deal', 'update', deal_input,
                                   selection_set)
        return self.execute(body)

    def delete_deal(self, id):
        """Execute `deleteDeal` mutation and return result.

        Parameters
        ----------
        id : str
            Deal id

        Returns
        -------
        GraphQLResponse
            Response from API
        """
        body = self._make_mutation('Deal', 'delete', {'id': id},
                                   'id')
        return self.execute(body)

    # -------------------------------------------------------------------------
    # Private

    def _make_mutation(self, model_type, mutation_type, input, selection_set):
        """Returns request body for mutations as configured by AWS Amplify.

        Parameters
        ----------
        model_type : str
            Description
        mutation_type : str
            Description (i.e. `create`, `delete`, or `update`)
        input : dict
            Description
        selection_set : str
            Selection set

        Returns
        -------
        dict:
            Description

            query: str
                Description
            variables: str
                Description

        Raises
        ------
        ValueError
            Invalid `mutation_type` or `input` for `delete` or `update` is
            missing `id`
        """
        # TODO: use assert instead?
        if mutation_type not in self.ALLOWED_MUTATION_ARGS:
            raise ValueError(
                f"Invalid mutation_type - Received '{mutation_type}'. "
                f"Valid values are {self.ALLOWED_MUTATION_ARGS}"
            )
        # `update` and `delete` mutation inputs must contain `id`
        if (
            mutation_type in ['delete', 'update']
            and (input.get('id', None) is None)
        ):
            raise ValueError(
                f'Mutation input for `{mutation_type}` mutation must contain `id`')  # noqa E501

        # `create` mutation cannot contain `_version` other than 0; just remove
        if mutation_type == 'create':
            input.pop('_version', None)

        prefix = f'{mutation_type.capitalize()}{model_type.capitalize()}'

        op_name = f'{prefix}Mutation'
        var_defs = f'$input: {prefix}Input!'
        op_field = f'{mutation_type.lower()}{model_type.capitalize()}'
        query = self._make_query('mutation', op_name, var_defs, op_field,
                                 'input: $input', selection_set)
        return {'query': query, 'variables': {'input': input}}

    def _make_query(self, op_type, op_name, var_defs, op_field, args,
                    selection_set):
        """Return value for `query` key in body of GraphQL request.

        Parameters
        ----------
        op_type : str
            GraphQL operation type (`query` or `mutation`)
        op_name : str
            A meaningful and explicit name for your GraphQL operation
        var_defs : str
            Variable definitions
        op_field : str
            Description
        args : str
            Description
        selection_set : str
            Selection set

        Returns
        -------
        str
            Value for `query` key in body of GraphQL request

        Raises
        ------
        ValueError
            Invalid `op_type`
        """
        if op_type not in self.ALLOWED_OPERATION_ARGS:
            raise ValueError(
                f"Invalid op_type - Received '{op_type}'. "
                f"Valid values are {self.ALLOWED_OPERATION_ARGS}"
            )

        return f'''{op_type} {op_name}({var_defs}) {{
            {op_field}({args}) {{
                {selection_set}
            }}
        }}
        '''

    def execute(self, body):
        """Send request with body and return result.

        Parameters
        ----------
        body : str
           Description

        Returns
        -------
        GraphQLResponse
           Response from API

        Raises
        ------
        requests.exceptions.RequestException
            Request failed
        """
        # try:
        resp = self.session.request(
            url=self.url,
            method='POST',
            json=body
        )
        resp.raise_for_status()
        # TODO: wrap requests exceptions
        # except RequestException as e:
        #     raise X
        # FIXME: `json()` can raise `ValueError` for invalid json; handle that?
        return GraphQLResponse(resp.json())
