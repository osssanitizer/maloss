<?php

require __DIR__ . '/vendor/autoload.php';
require_once('../php/GPBMetadata/Info.php');
require_once('../php/GPBMetadata/Info.php');
require_once('../php/GPBMetadata/Ast.php');
require_once('../php/GPBMetadata/Module.php');
require_once('../php/Proto/AstLookupConfig.php');
require_once('../php/Proto/AstNode.php');
require_once('../php/Proto/AstNode/NodeType.php');
require_once('../php/Proto/ModuleResult.php');
require_once('../php/Proto/ModuleSummary.php');

use Proto\AstLookupConfig;
use Proto\FileInfo;
use Proto\AstNode;
use Proto\AstNode\NodeType;
use Proto\ModuleResult;
use Proto\ModuleSummary;


function main() {
    $result = new Proto\ModuleResult();
    $summary = new Proto\ModuleSummary();
    $moduleResultPbFname = "module_result_php.pb";
    $moduleSummaryPbFname = "module_summary_php.pb";
    file_put_contents($moduleResultPbFname, $result->serializeToString());
    file_put_contents($moduleSummaryPbFname, $summary->serializeToString());
}

main();

?>
