<?php
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: class_sig.proto

namespace Proto;

use Google\Protobuf\Internal\GPBType;
use Google\Protobuf\Internal\RepeatedField;
use Google\Protobuf\Internal\GPBUtil;

/**
 * Generated from protobuf message <code>proto.MethodClassRelationProto</code>
 */
class MethodClassRelationProto extends \Google\Protobuf\Internal\Message
{
    /**
     * Generated from protobuf field <code>string methodname1 = 1;</code>
     */
    private $methodname1 = '';
    /**
     * Generated from protobuf field <code>string classname2 = 2;</code>
     */
    private $classname2 = '';

    /**
     * Constructor.
     *
     * @param array $data {
     *     Optional. Data for populating the Message object.
     *
     *     @type string $methodname1
     *     @type string $classname2
     * }
     */
    public function __construct($data = NULL) {
        \GPBMetadata\ClassSig::initOnce();
        parent::__construct($data);
    }

    /**
     * Generated from protobuf field <code>string methodname1 = 1;</code>
     * @return string
     */
    public function getMethodname1()
    {
        return $this->methodname1;
    }

    /**
     * Generated from protobuf field <code>string methodname1 = 1;</code>
     * @param string $var
     * @return $this
     */
    public function setMethodname1($var)
    {
        GPBUtil::checkString($var, True);
        $this->methodname1 = $var;

        return $this;
    }

    /**
     * Generated from protobuf field <code>string classname2 = 2;</code>
     * @return string
     */
    public function getClassname2()
    {
        return $this->classname2;
    }

    /**
     * Generated from protobuf field <code>string classname2 = 2;</code>
     * @param string $var
     * @return $this
     */
    public function setClassname2($var)
    {
        GPBUtil::checkString($var, True);
        $this->classname2 = $var;

        return $this;
    }

}
