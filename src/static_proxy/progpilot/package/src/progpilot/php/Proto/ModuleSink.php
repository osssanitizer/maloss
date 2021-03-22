<?php
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: module.proto

namespace Proto;

use Google\Protobuf\Internal\GPBType;
use Google\Protobuf\Internal\RepeatedField;
use Google\Protobuf\Internal\GPBUtil;

/**
 * Generated from protobuf message <code>proto.ModuleSink</code>
 */
class ModuleSink extends \Google\Protobuf\Internal\Message
{
    /**
     * Generated from protobuf field <code>.proto.AstNode node = 1;</code>
     */
    private $node = null;
    /**
     * Generated from protobuf field <code>repeated .proto.AstNode reachable_sinks = 2;</code>
     */
    private $reachable_sinks;

    /**
     * Constructor.
     *
     * @param array $data {
     *     Optional. Data for populating the Message object.
     *
     *     @type \Proto\AstNode $node
     *     @type \Proto\AstNode[]|\Google\Protobuf\Internal\RepeatedField $reachable_sinks
     * }
     */
    public function __construct($data = NULL) {
        \GPBMetadata\Module::initOnce();
        parent::__construct($data);
    }

    /**
     * Generated from protobuf field <code>.proto.AstNode node = 1;</code>
     * @return \Proto\AstNode
     */
    public function getNode()
    {
        return $this->node;
    }

    /**
     * Generated from protobuf field <code>.proto.AstNode node = 1;</code>
     * @param \Proto\AstNode $var
     * @return $this
     */
    public function setNode($var)
    {
        GPBUtil::checkMessage($var, \Proto\AstNode::class);
        $this->node = $var;

        return $this;
    }

    /**
     * Generated from protobuf field <code>repeated .proto.AstNode reachable_sinks = 2;</code>
     * @return \Google\Protobuf\Internal\RepeatedField
     */
    public function getReachableSinks()
    {
        return $this->reachable_sinks;
    }

    /**
     * Generated from protobuf field <code>repeated .proto.AstNode reachable_sinks = 2;</code>
     * @param \Proto\AstNode[]|\Google\Protobuf\Internal\RepeatedField $var
     * @return $this
     */
    public function setReachableSinks($var)
    {
        $arr = GPBUtil::checkRepeatedField($var, \Google\Protobuf\Internal\GPBType::MESSAGE, \Proto\AstNode::class);
        $this->reachable_sinks = $arr;

        return $this;
    }

}
