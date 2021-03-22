#!/bin/bash
# Install protoc 3.6.1, the latest version
# This is needed to compile proto files, i.e. run maloss/src/proto/gen.sh
# This is not needed to run the projects though.
# https://gist.github.com/rvegas/e312cb81bbb0b22285bc6238216b709b
VERSION=3.6.1

# Make sure you grab the latest version
curl -OL https://github.com/google/protobuf/releases/download/v$VERSION/protoc-$VERSION-linux-x86_64.zip

# Unzip
unzip protoc-$VERSION-linux-x86_64.zip -d protoc3

# Move protoc to /usr/local/bin/
sudo mv protoc3/bin/* /usr/local/bin/

# Move protoc3/include to /usr/local/include/
sudo mv protoc3/include/* /usr/local/include/

# Optional: change owner
# sudo chown $USER /usr/local/bin/protoc
# sudo chown -R $USER /usr/local/include/google

# Cleanup
rm -r protoc-$VERSION-linux-x86_64.zip protoc3
