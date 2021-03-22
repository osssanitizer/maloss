#!/bin/bash

PROGPILOT_DATA_DIR=../../src/static_proxy/progpilot/package/src/uptodate_data/php
cp $PROGPILOT_DATA_DIR/sources.json progpilot_sources.json
cp $PROGPILOT_DATA_DIR/sinks.json progpilot_sinks.json
cp $PROGPILOT_DATA_DIR/sanitizers.json ../static_php_sanitizers.json
cp $PROGPILOT_DATA_DIR/validators.json ../static_php_validators.json
cp $PROGPILOT_DATA_DIR/rules.json ../static_php_rules.json

