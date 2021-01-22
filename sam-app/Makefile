BASE := $(shell /bin/pwd)
PIPENV ?= pipenv

PIPENV_VENV_IN_PROJECT := 1
export PIPENV_VENV_IN_PROJECT

help:
	$(info ${HELP_MESSAGE})
	@exit 0

# install: ##=> Install pipenv
# 	$(info [*] Installing pipenv)
# 	@pip install pipenv --upgrade
# 	$(MAKE) dev

# https://github.com/aws-samples/cookiecutter-aws-sam-python
dev: ##=> Install dependencies
	$(info [*] Installing pipenv project dependencies)
	@$(PIPENV) install
	@$(PIPENV) install -d

# https://medium.com/@alexander.mancevice/python-applications-on-aws-lambda-e55bce85fea6
Pipfile.lock: Pipfile
	pipenv lock
	pipenv lock -r > requirements.txt
	pipenv lock -r -d > requirements-dev.txt

lock: Pipfile.lock

# build: ##=> Same as package except that we don't create a ZIP
# 	sam build --use-container

clean: ##=> Deletes current build environment and latest build
	$(info [*] Deleting SAM build environment...)
	rm -rf ./.aws-sam/

shell: ##=> Spawn a virtual environment shell
	@$(PIPENV) shell

invoke.deal: ##=> Run SAM Local function with a given event payload
	@sam local invoke DealCheckFunction --event events/event-deal_check.json

invoke.notification: ##=> Run SAM Local function with a given event payload
	@sam local invoke NotificationFunction --event events/event-push_potification.json

test: ##=> Run pytest
	$(PIPENV) run python -m unittest tests

.PHONY: help dev lock

#############
#  Helpers  #
#############

define HELP_MESSAGE
	Environment variables to be aware of or to hardcode depending on your use case:

	Common usage:

	...::: Installs Pipenv, application and dev dependencies defined in Pipfile :::...
	$ make install

	# ...::: Builds Lambda function dependencies:::...
	# $ make build

	...::: Locks Pipfile and generates requirements.txt :::...
	$ make lock

	# ...::: Deploy for the first time :::...
	# $ make deploy.guided

	# ...::: Deploy subsequent changes :::...
	# $ make deploy

	...::: Run unittest under tests/ with pipenv :::...
	$ make test

	...::: Run DealCheck local function :::...
	$ make invoke.deal

	...::: Run Notification local function :::...
	$ make invoke.notification

	...::: Spawn a virtual environment shell :::...
	$ make shell

	...::: Cleans up the environment - Deletes Virtualenv, ZIP builds and Dev env :::...
	$ make clean
endef
