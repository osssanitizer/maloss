<?php

// Return all registered __autoload() functions
// Run composer dumpautoload --optimize and then class map is located at: vendor/composer/autoload_classmap.php
$loader = require __DIR__ . '/vendor/autoload.php';


function tryInitModuleAttr($invocable, $inst) {
    echo "checking invocable ", $invocable, "\n";
    $paraNum = $invocable->getNumberOfParameters();
    $classStr = get_class($invocable);
    if ($classStr == "ReflectionFunction") {
        if ($paraNum == 0)
            $invocable->invoke();
        else
            $invocable->invokeArgs(array_fill(0, $paraNum, NULL));
    } elseif ($classStr == "ReflectionMethod") {
        if ($paraNum == 0)
            $invocable->invoke($inst);
        else
            $invocable->invokeArgs($inst, array_fill(0, $paraNum, NULL));
    } else {
        echo "Unexpected class str: ", $classStr, ", please consider handling!\n";
    }
}

// Timeout in Php
// https://packagist.org/packages/phpunit/php-invoker
// https://packagist.org/packages/react/promise-timer
function tryInitModuleAttrs($mod, $type) {
    echo "checking mod $mod type $type\n";
    $invoker = new PHP_Invoker();
    if ($type == "class") {
        // https://stackoverflow.com/questions/11575724/php-how-to-list-out-all-public-functions-of-class
        $class = new ReflectionClass($mod);
        echo "there are ", count($class->getMethods()), " total methods in class $mod\n";
        $static_methods = $class->getMethods(ReflectionMethod::IS_STATIC);
        echo "checking ", count($static_methods), " public static methods of class $mod\n";
        foreach($static_methods as $static_method) {
            try {
                $invoker->invoke(tryInitModuleAttr, [$static_method, NULL], 20);
                // tryInitModuleAttr($static_method, NULL);
            } catch (Throwable $e) {
                echo 'Caught exception: ',  $e->getMessage(), "\n";
            }
        }
        $inst = NULL;
        echo "trying to construct an instance for class $mod\n";
        if ($class->isInstantiable() && !is_null($class->getConstructor())) {
            try {
                $paraNum = $class->getConstructor()->getNumberOfParameters();
                if ($paraNum == 0)
                    $inst = $invoker->invoke($class->newInstance, [], 20);
                    // $class->newInstance();
                else
                    $inst = $invoker->invoke($class->newInstanceArgs, [array_fill(0, $paraNum, NULL)], 20);
                    // $class->newInstanceArgs(array_fill(0, $paraNum, NULL));
            } catch (Throwable $e) {
                echo 'Caught exception: ',  $e->getMessage(), "\n";
            }
        }
        // call all instance methods
        if (is_null($inst))
            return;
        $methods = $class->getMethods(ReflectionMethod::IS_PUBLIC);
        $instance_methods = array_diff($methods, $static_methods);
        echo "checking ", count($instance_methods),  " public instance methods of class $mod\n";
        foreach($instance_methods as $instance_method) {
            try {
                $invoker->invoke(tryInitModuleAttr, [$instance_method, $inst], 20);
                // tryInitModuleAttr($instance_method, $inst);
            } catch (Throwable $e) {
                echo 'Caught exception: ',  $e->getMessage(), "\n";
            }
        }
    } elseif ($type == "function") {
        try {
            $function = new ReflectionFunction($mod);
            $invoker->invoke(tryInitModuleAttr, [$function, NULL], 20);
            // tryInitModuleAttr($function, NULL);
        } catch (Throwable $e) {
            echo 'Caught exception: ',  $e->getMessage(), "\n";
        }
    } elseif ($type == "variable") {
        // $obj_cls = get_class($mod);
        throw new Exception("not handling type variable");
    } else {
        throw new Exception("unsupported module type $type");
    }
    // $loop = Factory::create();
    // Timer\timeout($promise, 20, $loop);
}

// FIXME: Classmap vs. PSR-0 vs. PSR-4, currently assuming all keys in class map to be classes
// https://medium.com/tech-tajawal/php-composer-the-autoloader-d676a2f103aa
function getModuleClasses($classMap, $name) {
    echo "checking ", count($classMap), " classes\n";
    $pkgPath = "vendor/" . $name . "/";
    $moduleClasses = array();
    foreach($classMap as $key => $value) {
        // How do I check if a string contains a specific word?
        // https://stackoverflow.com/questions/4366730/how-do-i-check-if-a-string-contains-a-specific-word
        if (strpos($value, $pkgPath) !== false) {
            $moduleClasses[] = $key;
        }
    }
    echo "found ", count($moduleClasses), " that belongs to ", $name, "\n";
    return $moduleClasses;
}

function getModuleFunctions($userFuncs, $name) {
    echo "checking ", count($userFuncs), " functions\n";
    $pkgPrefix = str_replace(array("-", "/"), "\\", $name);
    $moduleFunctions = array();
    foreach($userFuncs as $value) {
        if (strpos($value, $pkgPrefix) !== false && substr_count($value, "\\") == substr_count($pkgPrefix, "\\") + 1) {
            $moduleFunctions[] = $value;
        }
    }
    echo "found ", count($moduleFunctions), " that belongs to ", $name, "\n";
    return $moduleFunctions;
}

// Register a function for execution on shutdown
// https://www.php.net/manual/en/function.register-shutdown-function.php
function handleRemainingModules () {
    global $variables, $completedVariables, $classes, $completedClasses, $functions, $completedFunctions;
    $remainingVariables = array_diff($variables, $completedVariables);
    $remainingClasses = array_diff($classes, $completedClasses);
    $remainingFunctions = array_diff($functions, $completedFunctions);
    if (count($remainingVariables) == 0 && count($remainingClasses) == 0 && count($remainingFunctions) == 0)
        return;

    $error = error_get_last();
    echo "Caught fatal error, ignore and process the remaining\n";
    register_shutdown_function('handleRemainingModules');
    echo "Process remaining ", count($remainingVariables), " variables, ", count($remainingClasses), " classes, ", count($remainingFunctions), " functions\n";
    foreach($remainingVariables as $var) {
        $completedVariables[] = $var;
        tryInitModuleAttrs($var, "variable");
    }
    foreach($remainingFunctions as $func) {
        $completedFunctions[] = $func;
        tryInitModuleAttrs($func, "function");
    }
    foreach($remainingClasses as $cls) {
        $completedClasses[] = $cls;
        tryInitModuleAttrs($cls, "class");
    }
}

// Php command line features
// https://www.macs.hw.ac.uk/~hwloidl/docs/PHP/features.commandline.html
if ($argc != 2)
    exit("Usage: $argv[0] PKG_NAME\n");

// FIXME: global variables, functions and classes are possible targets. Currently, only exercising the latter two.
$variables = array();
$completedVariables = array();
// Get class map from loader
$classes = getModuleClasses($loader->getClassMap(), $argv[1]);
$completedClasses = array();
// PHP: Return all user-defined functions
// https://stackoverflow.com/questions/20447998/php-return-all-user-defined-functions
$functions = getModuleFunctions(get_defined_functions()['user'], $argv[1]);
$completedFunctions = array();
register_shutdown_function('handleRemainingModules');
echo "Process ", count($variables), " variables, ", count($classes), " classes, ", count($functions), " functions\n";
foreach($variables as $var) {
    $completedVariables[] = $var;
    tryInitModuleAttrs($var, "variable");
}
foreach($functions as $func) {
    $completedFunctions[] = $func;
    tryInitModuleAttrs($func, "function");
}
foreach($classes as $cls) {
    $completedClasses[] = $cls;
    tryInitModuleAttrs($cls, "class");
}

?>
