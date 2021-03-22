<?php
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: ast.proto

namespace Proto;

/**
 **
 * Types of taint sources and sinks
 * http://blogs.grammatech.com/what-is-taint-checking
 * http://web.cs.iastate.edu/~weile/cs513x/2018spring/taintanalysis.pdf
 * https://www.bodden.de/pubs/rab14classifying.pdf
 *
 * Protobuf type <code>proto.SourceType</code>
 */
class SourceType
{
    /**
     * Generated from protobuf enum <code>SOURCE_UNCLASSIFIED = 0;</code>
     */
    const SOURCE_UNCLASSIFIED = 0;
    /**
     * Sources from Susi
     *
     * Generated from protobuf enum <code>SOURCE_ACCOUNT = 1;</code>
     */
    const SOURCE_ACCOUNT = 1;
    /**
     * Generated from protobuf enum <code>SOURCE_BLUETOOTH = 2;</code>
     */
    const SOURCE_BLUETOOTH = 2;
    /**
     * Generated from protobuf enum <code>SOURCE_BROWSER = 3;</code>
     */
    const SOURCE_BROWSER = 3;
    /**
     * Generated from protobuf enum <code>SOURCE_CALENDAR = 4;</code>
     */
    const SOURCE_CALENDAR = 4;
    /**
     * Generated from protobuf enum <code>SOURCE_CONTACT = 5;</code>
     */
    const SOURCE_CONTACT = 5;
    /**
     * Generated from protobuf enum <code>SOURCE_DATABASE = 6;</code>
     */
    const SOURCE_DATABASE = 6;
    /**
     * Generated from protobuf enum <code>SOURCE_FILE = 7;</code>
     */
    const SOURCE_FILE = 7;
    /**
     * Generated from protobuf enum <code>SOURCE_NETWORK = 8;</code>
     */
    const SOURCE_NETWORK = 8;
    /**
     * Generated from protobuf enum <code>SOURCE_NFC = 9;</code>
     */
    const SOURCE_NFC = 9;
    /**
     * Generated from protobuf enum <code>SOURCE_SETTINGS = 10;</code>
     */
    const SOURCE_SETTINGS = 10;
    /**
     * Generated from protobuf enum <code>SOURCE_SYNC = 11;</code>
     */
    const SOURCE_SYNC = 11;
    /**
     * Generated from protobuf enum <code>SOURCE_UNIQUE_IDENTIFIER = 12;</code>
     */
    const SOURCE_UNIQUE_IDENTIFIER = 12;
    /**
     * Sources from other sources
     *
     * Generated from protobuf enum <code>SOURCE_ENVIRONMENT = 51;</code>
     */
    const SOURCE_ENVIRONMENT = 51;
    /**
     * Generated from protobuf enum <code>SOURCE_USER_INPUT = 52;</code>
     */
    const SOURCE_USER_INPUT = 52;
    /**
     * Generated from protobuf enum <code>SOURCE_OBFUSCATION = 53;</code>
     */
    const SOURCE_OBFUSCATION = 53;
}
