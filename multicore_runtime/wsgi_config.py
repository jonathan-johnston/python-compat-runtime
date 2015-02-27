# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Utilities to configure the dispatcher, middleware and environment."""

import logging
import os
import threading
from UserDict import UserDict

from google.appengine.api import appinfo_includes
from google.appengine.runtime import wsgi


def get_module_config_filename():
  """Returns the name of the module configuration file (app.yaml)."""
  module_yaml_path = os.environ['MODULE_YAML_PATH']
  logging.info('Using module_yaml_path from env: %s', module_yaml_path)
  return module_yaml_path


def get_module_config(filename):
  """Returns the parsed module config."""
  with open(filename) as f:
    return appinfo_includes.Parse(f)


def app_for_script(script):
  """Returns the WSGI app specified in the input string, or None on failure."""
  if script:
    app, filename, err = wsgi.LoadObject(script)  # pylint: disable=unused-variable
    if err:
      # Log the exception but do not reraise.
      logging.exception('Failed to import %s: %s', script, err)
      return None
    else:
      return app


def load_user_scripts_into_handlers(handlers):
  """Preloads user scripts.

  Args:
    handlers: appinfo_external.handlers data as provided by get_module_config()

  Returns:
    A list of tuples suitable for configuring the dispatcher() app,
    where the tuples are (url, script, app):
      - url: The url pattern which matches this handler.
      - script: The script to serve for this handler, as a string.
      - app: The fully loaded app corresponding to the script.
  """
  loaded_handlers = [
      (x.url,
       x.script.replace('$PYTHON_LIB/', '') if x.script else x.script,
       app_for_script(x.script) if x.script else None)
      for x in handlers]
  logging.info('Parsed handlers: %s',
               [(url, script) for (url, script, _) in loaded_handlers])
  return loaded_handlers


def env_vars_from_appengine_config(appengine_config):
  """Generate a dict suitable for updating os.environ to reflect app config.

  This function only returns a dict and does not update os.environ directly.

  Args:
    appengine_config: The app configuration as generated by
                      vmconfig.BuildVmAppengineEnvConfig()

  Returns:
    A dict of strings suitable for e.g. `os.environ.update(values)`.
  """

  return {'SERVER_SOFTWARE': appengine_config.server_software,
          'APPENGINE_RUNTIME': 'python27',
          'APPLICATION_ID': '%s~%s' % (appengine_config.partition,
                                       appengine_config.appid),
          'INSTANCE_ID': appengine_config.instance,
          'BACKEND_ID': appengine_config.major_version,
          'CURRENT_MODULE_ID': appengine_config.module,
          'CURRENT_VERSION_ID': '%s.%s' % (appengine_config.major_version,
                                           appengine_config.minor_version),
          'DEFAULT_TICKET': appengine_config.default_ticket}


def user_env_vars_from_appinfo_external(appinfo_external):
  """Generate a dict of env variables specified by the user in app.yaml.

  This function only returns a dict and does not update os.environ directly.

  Args:
    appinfo_external: The app.yaml configuration info as generated by
                      get_module_config()

  Returns:
    A dict of strings suitable for e.g. `os.environ.update(values)`.
  """

  return appinfo_external.env_variables or {}


# Dictionary with thread-local contents.
class ThreadLocalDict(UserDict, threading.local):
  pass