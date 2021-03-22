<?php

require __DIR__ . '/vendor/autoload.php';
require_once('../proto/php/GPBMetadata/ClassSig.php');
require_once('../proto/php/GPBMetadata/Ast.php');
require_once('../proto/php/Proto/PkgAstResult.php');
require_once('../proto/php/Proto/PkgAstResults.php');
require_once('../proto/php/Proto/AstLookupConfig.php');
require_once('../proto/php/Proto/FileInfo.php');
require_once('../proto/php/Proto/Language.php');
require_once('../proto/php/Proto/SourceLocation.php');
require_once('../proto/php/Proto/SourceRange.php');
require_once('../proto/php/Proto/AstNode.php');
require_once('../proto/php/Proto/AstNode/NodeType.php');

use GetOpt\GetOpt;
use GetOpt\Option;
use PhpParser\Error;
use PhpParser\NodeDumper;
use PhpParser\ParserFactory;
use PhpParser\Lexer\Emulative;
use PhpParser\Node;
use PhpParser\Node\Stmt\Function_;
use PhpParser\Node\Stmt\Expression;
use PhpParser\Node\Expr\FuncCall;
use PhpParser\Node\Expr\Eval_;
use PhpParser\Node\Expr\ShellExec;
use PhpParser\Node\Expr\MethodCall;
use PhpParser\NodeTraverser;
use PhpParser\NodeVisitorAbstract;
use Proto\PkgAstResults;
use Proto\PkgAstResult;
use Proto\AstLookupConfig;
use Proto\FileInfo;
use Proto\Language;
use Proto\SourceLocation;
use Proto\SourceRange;
use Proto\AstNode;
use Proto\AstNode\NodeType;


function parseArgs() {
    // Parse command line options
    // http://php.net/manual/en/function.getopt.php
    // http://getopt-php.github.io/getopt-php/
    $optionInpath = new \GetOpt\Option('i', 'inpath', \GetOpt\GetOpt::REQUIRED_ARGUMENT);
    $optionInpath->setDescription('Path to the input directory or file.');
    $optionConfig = new \GetOpt\Option('c', 'config', \GetOpt\GetOpt::REQUIRED_ARGUMENT);
    $optionConfig->setDescription('Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).');
    $optionOutfile = new \GetOpt\Option('o', 'outfile', \GetOpt\GetOpt::REQUIRED_ARGUMENT);
    $optionOutfile->setDescription('Path to the output file.');
    $optionRoot = new \GetOpt\Option('b', 'root', \GetOpt\GetOpt::OPTIONAL_ARGUMENT);
    $optionRoot->setDescription('Path to the root of the source.');
    $optionName = new \GetOpt\Option('n', 'package_name', \GetOpt\GetOpt::OPTIONAL_ARGUMENT);
    $optionName->setDescription('Package name of the specified input.');
    $optionVersion = new \GetOpt\Option('v', 'package_version', \GetOpt\GetOpt::OPTIONAL_ARGUMENT);
    $optionVersion->setDescription('Package version of the specified input.');
    $optionHelp = new \GetOpt\Option('h', 'help', \GetOpt\GetOpt::NO_ARGUMENT);
    $optionHelp->setDescription('Show this help and quit');
    $getopt = new \GetOpt\GetOpt();
    $getopt->addOptions([$optionInpath, $optionConfig, $optionOutfile, $optionRoot, $optionName, $optionVersion,
        $optionHelp]);
    return $getopt;
}

function endsWith($haystack, $needle)
{
    // https://stackoverflow.com/questions/834303/startswith-and-endswith-functions-in-php
    $length = strlen($needle);
    return $length === 0 ||
        (substr($haystack, -$length) === $needle);
}

function getInfiles($inpath, $root) {
    // http://php.net/manual/en/class.recursivedirectoryiterator.php
    $infiles = array();
    if (file_exists($inpath)) {
        if (is_dir($inpath)) {
            $objects = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($inpath));
            foreach($objects as $name => $object){
                if (endsWith($name, '.php')) {
                    $infiles[] = realpath($name);
                }
            }
            if (is_null($root))
                $root = $inpath;
            $root = realpath($root);
        } else {
            $infiles[] = realpath($inpath);
            if (is_null($root))
                $root = dirname($inpath);
            $root = realpath($root);
        }
    } else{
        throw new Exception("inpath $inpath doesn't exist!");
    }
    return array($infiles, $root);
}


class PhpDeclRefVisitor extends NodeVisitorAbstract {
    private $code;
    private $declRefsFilterSet;
    private $debug;
    private $declRefs;

    public function __construct($code, $configpb, $debug) {
        $this->code = $code;
        $this->debug = $debug;
        $this->saveFeature = false;
        $this->funcOnly = false;
        if (!is_null($configpb)) {
            $this->saveFeature = $configpb->getSaveFeature();
            $this->funcOnly = $configpb->getFuncOnly();
        }

        // initialize the declaration filters
        $this->declRefsFilterSet = NULL;
        if (!is_null($configpb)) {
            $this->declRefsFilterSet = array();
            foreach($configpb->getApis() as $api) {
                if ($api->getType() === \Proto\AstNode\NodeType::FUNCTION_DECL_REF_EXPR) {
                    if ($this->funcOnly) {
                        if (!empty($api->getBaseType()))
                            $nameToCheck = '->' . $api->getName();
                        else
                            $nameToCheck = $api->getName();
                        $this->declRefsFilterSet[$nameToCheck] = 1;
                    } else {
                        $this->declRefsFilterSet[$api->getFullName()] = 1;
                    }
                }
            }
        }
        // the collected declaration references
        $this->declRefs = array();
    }

    public function getDeclRefs() {
        return $this->declRefs;
    }

    public function leaveNode(Node $node) {
        $declRef = array();
        if ($node instanceof FuncCall) {
            echo "visiting Call node\n";
            // Fields: name, args, attributes
            $declRef['name'] = $this->getSourceText($this->code, $node->name);
            $declRef['base'] = NULL;
            $declRef['source_range'] = $this->getPosition($node);
            $declRef['source_text'] = $this->getSourceText($this->code, $node);
            $argArr = array();
            foreach($node->args as $arg) {
                $argArr[] = $this->getSourceText($this->code, $arg);
            }
            $declRef['args'] = $argArr;
            $fullName = $declRef['name'];
        } elseif($node instanceof Eval_) {
            echo "visiting Eval_ node\n";
            $declRef['name'] = 'eval';
            $declRef['base'] = NULL;
            $declRef['source_range'] = $this->getPosition($node);
            $declRef['source_text'] = $this->getSourceText($this->code, $node);
            // eval takes only one argument
            $argArr = array();
            $argArr[] = $this->getSourceText($this->code, $node->expr);
            $declRef['args'] = $argArr;
            $fullName = $declRef['name'];
        } elseif($node instanceof MethodCall) {
            echo "visiting MethodCall node\n";
            // Fields: var, name, args, attributes
            $declRef['name'] = $this->getSourceText($this->code, $node->name);
            $declRef['base'] = $this->getSourceText($this->code, $node->var);
            $declRef['source_range'] = $this->getPosition($node);
            $declRef['source_text'] = $this->getSourceText($this->code, $node);
            $argArr = array();
            foreach($node->args as $arg) {
                $argArr[] = $this->getSourceText($this->code, $arg);
            }
            $declRef['args'] = $argArr;
            $fullName = $declRef['base'] . '.' . $declRef['name'];
        } elseif($node instanceof ShellExec) {
            echo "visiting ShellExec node\n";
            // backtick operator is equivalent to shell_exec
            $declRef['name'] = 'shell_exec';
            $declRef['base'] = NULL;
            $declRef['source_range'] = $this->getPosition($node);
            $declRef['source_text'] = $this->getSourceText($this->code, $node);
            // shell_exec takes only one argument
            $argArr = array();
            $argArr[] = $this->getSourceText($this->code, $node->parts[0]);
            $declRef['args'] = $argArr;
            $fullName = $declRef['name'];
        } elseif($node instanceof Function_) {
            echo "visiting Function_ node\n";
        } else {
            echo "visiting ", get_class($node), " node\n";
        }
        if (array_key_exists('name', $declRef)) {
            if ($this->funcOnly) {
                if (array_key_exists('base', $declRef) && !is_null($declRef['base'])) {
                    $nameToCheck = '->' . $declRef['name'];
                } else {
                    $nameToCheck = $declRef['name'];
                }
            } else {
                $nameToCheck = $fullName;
            }
            if (is_null($this->declRefsFilterSet) ||
                    array_key_exists($nameToCheck, $this->declRefsFilterSet)) {
                $this->declRefs[] = $declRef;
            }
        }
    }

    // Adapted from NodeDumper class
    private function getPosition(Node $node) {
        $position = array();
        if (!$node->hasAttribute('startLine') || !$node->hasAttribute('endLine')) {
            return null;
        }
        $position['start_line'] = $node->getStartLine();
        $position['end_line'] = $node->getEndLine();
        if ($node->hasAttribute('startFilePos') && $node->hasAttribute('endFilePos')
            && null !== $this->code) {
            $position['start_column'] = $this->toColumn($this->code, $node->getStartFilePos());
            $position['end_column'] = $this->toColumn($this->code, $node->getEndFilePos());
        }
        return $position;
    }

    private function getSourceText($code, $node) {
        if ($node->hasAttribute('startFilePos') && $node->hasAttribute('endFilePos')
            && null !== $this->code) {
            return substr($code, $node->getStartFilePos(),
                $node->getEndFilePos() - $node->getStartFilePos() + 1);
        } else
            return "";
    }

    // Copied from Error class
    private function toColumn($code, $pos) {
        if ($pos > strlen($code)) {
            throw new \RuntimeException('Invalid position information');
        }
        $lineStartPos = strrpos($code, "\n", $pos - strlen($code));
        if (false === $lineStartPos) {
            $lineStartPos = -1;
        }
        return $pos - $lineStartPos;
    }

}

function relativePath($from, $to, $ps = DIRECTORY_SEPARATOR)
{
    $arFrom = explode($ps, rtrim($from, $ps));
    $arTo = explode($ps, rtrim($to, $ps));
    while(count($arFrom) && count($arTo) && ($arFrom[0] == $arTo[0]))
    {
        array_shift($arFrom);
        array_shift($arTo);
    }
    return str_pad("", count($arFrom) * 3, '..'.$ps).implode($ps, $arTo);
}

function getFilepb($infile, $root) {
    $filepb = new \Proto\FileInfo();
    $filepb->setFilename(basename($infile));
    $filepb->setRelpath(relativePath($root, dirname($infile)));
    $filepb->setFile(relativePath($root, $infile));
    $filepb->setDirectory($root);
    return $filepb;
}

function getApiResultpb($base, $name, $args, $source_text, $source_range, $filepb) {
    $apiResultpb = new \Proto\AstNode();
    $apiResultpb->setType(\Proto\AstNode\NodeType::FUNCTION_DECL_REF_EXPR);
    $apiResultpb->setName($name);
    if (is_null($base))
        $apiResultpb->setFullName($name);
    else {
        $apiResultpb->setBaseType($base);
        $apiResultpb->setFullName($base . '.' . $name);
    }
    foreach($args as $arg) {
        $argspb = $apiResultpb->getArguments();
        $argspb[] = $arg;
        $apiResultpb->setArguments($argspb);
    }
    $apiResultpb->setSource($source_text);
    $startLocpb = new \Proto\SourceLocation();
    $startLocpb->setRow($source_range['start_line']);
    $startLocpb->setColumn($source_range['start_column']);
    $startLocpb->setFileInfo($filepb);
    $endLocpb = new \Proto\SourceLocation();
    $endLocpb->setRow($source_range['end_line']);
    $endLocpb->setColumn($source_range['end_column']);
    $endLocpb->setFileInfo($filepb);
    $rangepb = new \Proto\SourceRange();
    $rangepb->setStart($startLocpb);
    $rangepb->setEnd($endLocpb);
    $apiResultpb->setRange($rangepb);
    return $apiResultpb;
}

function phpAstGen($inpath, $outfile, $configpb, $root, $pkg_name, $pkg_version) {
    // Google Protobuf for Php
    // https://docs.google.com/document/d/1fUi0lKpfR7gauaJdhjid1SStdLePREVeUnwfamrPRVk/edit#heading=h.v03byv1vu6dr
    // Read code from file
    list($infiles, $root) = getInfiles($inpath, $root);

    // initialize resultpb
    $pkg = new \Proto\PkgAstResult();
    $pkg->setConfig($configpb);
    if (!is_null($pkg_name))
        $pkg->setPkgName($pkg_name);
    else
        $pkg->setPkgName(basename($inpath));
    if (!is_null($pkg_version))
        $pkg->setPkgVersion($pkg_version);
    $pkg->setLanguage(\Proto\Language::PHP);
    foreach($infiles as $infile) {
        echo "analyzing $infile\n";
        $code = file_get_contents($infile);
        $lexer = new Emulative(['usedAttributes' => [
            'startLine', 'endLine', 'startFilePos', 'endFilePos', 'comments'
        ]]);
        $parser = (new ParserFactory)->create(ParserFactory::PREFER_PHP7, $lexer);
        try {
            $ast = $parser->parse($code);
        } catch (Error $error) {
            echo "Parse error: {$error->getMessage()}\n";
            return;
        }

        $visitor = new PhpDeclRefVisitor($code, $configpb, false);
        $traverser = new NodeTraverser();
        $traverser->addVisitor($visitor);
        $traverser->traverse($ast);

        $filepb = getFilepb($infile, $root);
        foreach($visitor->getDeclRefs() as $declRef) {
            $apiResultpb = getApiResultpb($declRef['base'], $declRef['name'],
                $declRef['args'], $declRef['source_text'], $declRef['source_range'], $filepb);
            $apiResults = $pkg->getApiResults();
            $apiResults[] = $apiResultpb;
            $pkg->setApiResults($apiResults);
        }
    }

    $resultpb = new \Proto\PkgAstResults();
    $pkgspb = $resultpb->getPkgs();
    $pkgspb[] = $pkg;
    $resultpb->setPkgs($pkgspb);

    // save resultpb
    file_put_contents($outfile, $resultpb->serializeToString());
}

function main() {
    // Parse options
    $getopt = parseArgs();
    $getopt->process();
    $inpath = $getopt->getOption('inpath');
    $outfile = $getopt->getOption('outfile');
    $config = $getopt->getOption('config');
    $root = $getopt->getOption('root');
    $pkg_name = $getopt->getOption('package_name');
    $pkg_version = $getopt->getOption('package_version');

    // Show help and quit
    if ($getopt->getOption('help')) {
        echo $getopt->getHelpText();
        exit;
    }

    // Load config pb
    $configStr = file_get_contents($config);
    $configpb = new \Proto\AstLookupConfig();
    $configpb->mergeFromString($configStr);

    // Run the ast generation
    phpAstGen($inpath, $outfile, $configpb, $root, $pkg_name, $pkg_version);
}

main();

?>
