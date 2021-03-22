#!/bin/bash

if [ ! -f "xsd2thrift/target/xsd2thrift-1.0.jar" ]
then
    echo "building xsd2thrift"
    cd xsd2thrift && mvn -DskipTests install && cd ../
fi

echo "Converting xsd format to proto formats"
java -jar xsd2thrift/target/xsd2thrift-1.0.jar --protobuf --filename=proto/summary_metadata.proto --package=proto.flowdroid ./soot-infoflow-summaries/schema/SummaryMetaData.xsd
java -jar xsd2thrift/target/xsd2thrift-1.0.jar --protobuf --filename=proto/class_summary.proto --package=proto.flowdroid ./soot-infoflow-summaries/schema/ClassSummary.xsd
java -jar xsd2thrift/target/xsd2thrift-1.0.jar --protobuf --filename=proto/flowdroid_configuration.proto --package=proto.flowdroid ./soot-infoflow-cmd/schema/FlowDroidConfiguration.xsd
java -jar xsd2thrift/target/xsd2thrift-1.0.jar --protobuf --filename=proto/source_sinks.proto --package=proto.flowdroid ./soot-infoflow-cmd/schema/SourcesAndSinks.xsd

