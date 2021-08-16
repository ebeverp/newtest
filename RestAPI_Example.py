#
# Copyright 2019 Perforce Software Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this 
# software and associated documentation files (the "Software"), to deal in the Software 
# without restriction, including without limitation the rights to use, copy, modify, 
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
# permit persons to whom the Software is furnished to do so, subject to the following 
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies 
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE 
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.
#
# NOTE: This script has only been tested with Python 3.6.2.

import urllib
import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import base64

#################################
# Begin Configuration Variables #
#################################
# URL of the Helix ALM REST API
HELIX_ALM_REST_API_URL = 'https://localhost:8443/helix-alm/api/v0/'

# Helix ALM login username
USER_NAME = 'administrator'

# Helix ALM login password
PASSWORD = ''

# Helix ALM project name
PROJECT_NAME = 'Traditional Template'

# SSL context to use if using https
#  	When using a self-signed certificate, a SSL: CERTIFICATE_VERIFY_FAILED error is returned.
#   If the certificate is trusted, change ssl.CERT_REQUIRED to ssl.CERT_NONE.
SSL_CERTIFICATE_MODE = ssl.CERT_NONE

# Supported SSL protocol
# By default, PROTOCOL_SSLV23 supports SSL2, SSL3, TLS, and SSL
SSL_PROTOCOL_MODE = None

# Sets up the the project name to be URL safe
PROJECT_NAME = urllib.parse.quote(PROJECT_NAME)


class HALMResponse:
  """
  This class exists to make it easier to work with the Helix ALM REST API responses. The 'is_success' function checks
  if a response was successful and the 'has_data' function makes it easier to check if there is data on the response.
  """
  def __init__(self, status_code=0, data=None):
    """
    Initializes a Helix ALM response object
    :param number status_code: HTTP status code for the response
    :param dict data: Result data. Could be None if there is no data.
    """
    self.status_code = status_code
    self.data = data

  def is_success(self):
    """ Basic function that checks if the response indicated success """
    return 200 <= self.status_code < 300

  def has_data(self):
    """ Basic function that checks if the response has data """
    return self.data is not None

  def set_http_error(self, error, status_code=None):
    """
    Helper function. If an error is returned from the Helix ALM REST API via an HTTP response, this ensures the
    HALMResponse is properly initialized with the error values.

    Helix ALM REST API errors generally follow this structure:
        {
          "code": "Bad Request",
          "statusCode": 400,
          "message": "This is information why the request failed",
          "errorElementPath": "/path/to/the/parameter/object/that/failed"
        }

    :param dict error: - Error response from the Helix ALM REST API Server
    :param number status_code: Optional status code to set. If not specified, attempts to use the status code on
                                the error. If the passed-in error does not have a 'statusCode' property and there was
                                no previous status_code set on this object, the status_code defaults to 500.
    """
    self.data = error

    if status_code is None and 'statusCode' in error:
      self.status_code = error['statusCode']
    elif status_code is None:
      self.status_code = 500
    else:
      self.status_code = status_code

  def set_error(self, message, status_code=None):
    """
    If the script triggers an error, a HALMResponse type object should be initialized to make handling the
    error easier. This 'translates' a Python error message into a value that can be printed via 'print_errors'.

    :param string message: Message to set as an error
    :param number status_code: Status code to set
    """
    # Sets up a default value for the status code based on the current status code value
    if status_code is None:
      status_code = self.status_code

    # Checks to make sure any existing data is not overwritten
    if not self.has_data():
      self.data = {}

    # Saves the provided status_code
    self.status_code = status_code

    # Checks to make sure existing errors are not overwritten
    if not hasattr(self.data, 'error') and not hasattr(self.data, 'error'):
      self.data['error'] = {'message': message, 'statusCode': self.status_code, 'code': ''}

  def print_errors(self):
    """
    Prints any errors that exist on the response
          format: <status_code> - <text_status_code> - <error message>
         example: 500 - Internal Server Error - An error occurred while processing the request.
    """
    if not self.is_success() and self.has_data():
      if 'error' in self.data:
        HALMResponse._print_errors([self.data['error']])
      elif 'errors' in self.data:
        HALMResponse._print_errors(self.data['errors'])
      elif not self.is_success() and self.has_data():
        # Assume that the current 'data' is an error object
        HALMResponse._print_errors([self.data])
      else:
        print("Response indicates failure, but there are no errors to print.")

  @classmethod
  def _print_errors(cls, errors):
    """
    Helper method that prints the errors in an error array

    :param list[dict] errors: List of potential errors returned from the REST API
    """
    for error in errors:
      print("{0} - {1} - {2}".format(error['statusCode'], error['code'], error['message']))

# --------------------------------------------------------------------------
# ------------------- Helix ALM REST API Example Methods -------------------
# --------------------------------------------------------------------------




def getAuthorization(accessToken=None):
  # """
  # Builds the authorization string.
  # :param dict accessToken: (optional) If specified, this should be an object with an 'accessToken' property
  # :return: Returns the value to store in the 'authorization' header
  # :rtype str
  # """
    if accessToken is None:
      authStr = USER_NAME + ':' + PASSWORD
      authStr = base64.b64encode(authStr.encode("utf-8")).decode("utf-8")
      authStr = 'basic ' + authStr
    else:
      authStr = 'Bearer ' + accessToken['accessToken']

    return authStr




def sendRequest(url, accessToken=None, requestBody=None, requestMethod=None):
  """
  Main function for communicating with the Helix ALM REST API. Handles sending the HTTP request and parsing the
  result.

  :param string url: REST API resource to connect to (Example: issues/15/events)
  :param dict accessToken: (Default: No token) If no token is provided, uses 'basic' authentication with a
                             username and password
  :param object requestBody: (Default: Empty) Object is serialized to JSON and sent to the server as the request body
  :param string requestMethod: (Default: GET ) Examples: GET, PUT, POST, DELETE
  :return: Returns the response data and response status code
  :rtype HALMResponse
  """
  result = HALMResponse()

  response = None
  try:
    # Encodes the Python objects as an HTTP request with JSON
    httpRequest = urllib.request.Request(HELIX_ALM_REST_API_URL + url)
    httpRequest.add_header('authorization', getAuthorization(accessToken))

    # Adds the request body, if provided
    if requestBody is not None:
      httpRequest.data = json.dumps(requestBody).encode()
      httpRequest.add_header('Content-Type', 'application/json')

    # Adds the request method, if provided
    if requestMethod is not None:
      httpRequest.method = requestMethod

    # Checks how SSL is handled
    ssl_context = ssl.create_default_context()

    if SSL_CERTIFICATE_MODE == ssl.CERT_NONE:
      ssl_context.check_hostname = False

    ssl_context.verify_mode = SSL_CERTIFICATE_MODE

    # Sends the request and handles the response
    response = urllib.request.urlopen(httpRequest, context=ssl_context)
    data = response.read()
    response.close()

  except urllib.error.HTTPError as e:
    t = e.fp.read()
    result.set_http_error(json.loads(t.decode("utf-8")), e.code)
  except urllib.error.URLError as e2:
    result.set_error(e2.reason)
    print("An error occurred when attempting to connect to {0}.\n"
          "\tTroubleshooting advice: Is your REST API server running at that address? "
          "If you open {0}versions in a browser, do you see a JSON response?"
          .format(HELIX_ALM_REST_API_URL))
  except Exception as e3:
    result.set_error(e3.args[0])
  else:
    # No exceptions, which means there could be resulting data. Checks and parses it.
    if len(data) > 0:
      result.data = json.loads(str(data, encoding='utf-8'))

  # If a response was returned, loads the status_code from it to the result
  if response is not None:
    result.status_code = response.status

  # If the result indicates an error occurred, attempts to print information about the error
  if not result.is_success():
    result.print_errors()

  return result




def GetProjectList():
  """
   Gets a list of all projects from the Helix ALM Server. Only includes projects the logged in user can access.

  Prints the resulting list of projects retrieved
  """
  projectListResult = sendRequest("projects")
  if projectListResult.is_success():
    print('Projects = ' + str(len(projectListResult.data['projects'])))
    for project in projectListResult.data['projects']:
      print(project['name'])
  else:
    print('Failed to retrieve projects.')
    if projectListResult.status_code == 500:
      print('\tTroubleshooting advice: Is the Helix ALM Server running? Check the REST API "helixAlmHostName" and '
            '"helixAlmPort" in the helix-alm-rest-api/config/config.json file.')



def GetAccessToken():
  """
  Shows an Authorization header using Basic authentication with the username Administrator and empty password
  :return: Returns an object that contains the accessToken or None if retrieving the access token failed
  """
  accessTokenResult = sendRequest('{0}/token'.format(PROJECT_NAME))
  if accessTokenResult.is_success():
    return accessTokenResult.data

  return None


def AddWorkflowEventExample(accessToken):
  """
  Posts a workflow event

  :param dict accessToken: An object that contains an access token
  """

  # Sets up the event data to send to the server
  eventsData = {
    "eventsData": [{
      "name": "Comment",
      "fields": [
        {
          "label": "Notes",
          "type": "string",
          "string": "Comment added by REST API"
        },
        {
          "label": "Date",
          "type": "dateTime",
          "dateTime": "2019-01-04T12:46:37Z"
        }
      ]
    }]
  }

  issueID = 4

  # Builds the request URL and sends the request
  url = '{0}/issues/{1}/events'.format(PROJECT_NAME, issueID)
  response = sendRequest(url, accessToken, eventsData, 'POST')
  if response.is_success():
    print('Added workflow event ' + str(response.data['eventsData'][0]['id']))
  else:
    print('Failed to add workflow event to issue with ID {0}'.format(issueID))

def GenerateAndPassTestRun(accessToken):
  """
  Generates a test run and then enters a workflow event to pass the test run
  :param dict accessToken: An object that contains an access token
  """
  testcaseID = 4

  # Builds the request URL to generate test runs
  url = "{0}/testruns/generate".format(PROJECT_NAME)

  # Builds the body parameter used to generate test runs
  requestBody = {
    "testCaseIDs": [testcaseID],  # Test cases used to generate the test runs
    "testRunSet": {
      "label": "Alpha 1 Tests"    # Test run set that the generated test runs will be added to
    },
    "variants": [                 # List of test variants to use to generate test runs
      {
        "label": "Operating System",
        "menuItemArray": [
          {"label": "Windows"}
        ]
      },
      {
        "label": "Database",
        "menuItemArray": [
          {"label": "Native"}
        ]
      },
      {
        "label": "Client Type",
        "menuItemArray": [
          {"label": "Web"}
        ]
      }
    ],
    "eventsData": [               # Workflow events to apply to the generated test runs
      {
        "name": "Pass",
        "fields": [
          {
            "label": "Notes",
            "type": "string",
            "string": "Passed by REST API"
          }
        ]
      }
    ]
  }


#MAIN
    
if __name__ == '__main__':


# Gets an access token for the PROJECT_NAME using USER_NAME and PASSWORD
    accessTokenObj = GetAccessToken()
# Adds a new Comment workflow event to the issue with ID 4
    AddWorkflowEventExample(accessTokenObj)
# Generates a test run from a test case and adds a Pass workflow event to it
    GenerateAndPassTestRun(accessTokenObj)
  
    projects = GetProjectList()

  
