<?php
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: class_sig.proto

namespace Proto;

use Google\Protobuf\Internal\GPBType;
use Google\Protobuf\Internal\RepeatedField;
use Google\Protobuf\Internal\GPBUtil;

/**
 * Generated from protobuf message <code>proto.ClassMethodRelationProto</code>
 */
class ClassMethodRelationProto extends \Google\Protobuf\Internal\Message
{
    /**
     * Generated from protobuf field <code>string classname1 = 1;</code>
     */
    private $classname1 = '';
    /**
     * Generated from protobuf field <code>string methodname2 = 2;</code>
     */
    private $methodname2 = '';

    /**
     * Constructor.
     *
     * @param array $data {
     *     Optional. Data for populating the Message object.
     *
     *     @type string $classname1
     *     @type string $methodname2
     * }
     */
    public function __construct($data = NULL) {
        \GPBMetadata\ClassSig::initOnce();
        parent::__construct($data);
    }

    /**
     * Generated from protobuf field <code>string classname1 = 1;</code>
     * @return string
     */
    public function getClassname1()
    {
        return $this->classname1;
    }

    /**
     * Generated from protobuf field <code>string classname1 = 1;</code>
     * @param string $var
     * @return $this
     */
    public function setClassname1($var)
    {
        GPBUtil::checkString($var, True);
        $this->classname1 = $var;

        return $this;
    }

    /**
     * Generated from protobuf field <code>string methodname2 = 2;</code>
     * @return string
     */
    public function getMethodname2()
    {
        return $this->methodname2;
    }

    /**
     * Generated from protobuf field <code>string methodname2 = 2;</code>
     * @param string $var
     * @return $this
     */
    public function setMethodname2($var)
    {
        GPBUtil::checkString($var, True);
        $this->methodname2 = $var;

        return $this;
    }

}
