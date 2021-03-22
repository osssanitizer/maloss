/*
 * Names for built-in types
 * https://www.npmjs.com/package/argparse
 * https://medium.freecodecamp.org/requiring-modules-in-node-js-everything-you-need-to-know-e7fbd119be8
 */

/*
 * If you require a module, Node.js looks for it by going through all node_modules/ directories in ancestor directories
 * (./node_modules/, ../node_modules/, ../../node_modules/, etc.). The first appropriate module that is found is used.
 *
 * http://2ality.com/2016/01/locally-installed-npm-executables.html
 */

// http://bluebirdjs.com/docs/api/timeout.html
var pt = require('promise-timeout');
const exitHook = require('exit-hook');


// FIXME: for debugging
function sleep(ms) {
    var unixtime_ms = new Date().getTime();
    while(new Date().getTime() < unixtime_ms + ms) {}
}


function isConstructor(obj) {
    return !!obj.prototype && !!obj.prototype.constructor.name;
}


function tryCallFunction(funcObj) {
    // FIXME: the function invocation is not interrupted after timeout
    // Function is callable and constructable
    // https://stackoverflow.com/questions/40922531/how-to-check-if-a-javascript-function-is-a-constructor
    if (isConstructor(funcObj)) {
        // console.log("invoking constructor function " + funcObj);
        var instObj = new funcObj();
        tryInitModuleAttrs(instObj);
    }
    else {
        // console.log("invoking normal function " + funcObj);
        funcObj();
    }
}


function tryInitModuleAttrs(mod) {
    // https://stackoverflow.com/questions/1249531/how-to-get-a-javascript-objects-class
    // https://stackoverflow.com/questions/359494/which-equals-operator-vs-should-be-used-in-javascript-comparisons
    if (mod.name === undefined) {
        console.log("checking object type " + typeof(mod));
    } else {
        console.log("checking mod " + mod.name + " type " + typeof(mod));
    }

    // check the mod itself if it's a function
    var modType = typeof(mod);
    console.log("checking mod type " + modType);
    if (modType === "function") {
        pt.timeout(new Promise((resolve, reject) => {
                    console.log("invoking mod type " + modType);
                    tryCallFunction(mod);
                    resolve();
                }), 20000)
            .then(function (thing) {
                // console.log('done!');
            }).catch(function (err) {
                if (err instanceof pt.TimeoutError) {
                    console.error("timeout!");
                } else {
                    console.error("unknown error: " + err + " !");
                }
            });
    }

    // check the attributes of the mod
    for (var attr in mod) {
        if (!mod.hasOwnProperty(attr))
            continue;
        // typeof(mod) == "function"
        // https://stackoverflow.com/questions/7440001/iterate-over-object-keys-in-node-js
        // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/typeof
        var attrType = typeof(mod[attr]);
        console.log("checking attr " + attr + " type " + attrType);
        var ignoreSet = new Set(["boolean", "number", "string", "symbol", "undefined"]);
        if (attrType === "function") {
            // Promise.race
            // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/race
            // https://stackoverflow.com/questions/46376432/understanding-promise-race-usage
            pt.timeout(new Promise((resolve, reject) => {
                        console.log("invoking mod " + mod.name + " attr " + attr);
                        tryCallFunction(mod[attr]);
                        resolve();
                    }), 20000)
                .then(function (thing) {
                    // console.log('done!');
                }).catch(function (err) {
                    if (err instanceof pt.TimeoutError) {
                        console.error("timeout!");
                    } else {
                        console.error("unknown error: " + err + " !");
                    }
                });
        } else if (attrType === "object") {
            // ignore null objects
            if (mod[attr] == null)
                continue;
            if (mod[attr].name === undefined) {
                // object without name field is an instance.
                try {
                    tryInitModuleAttrs(mod[attr]);
                } catch (err) {
                    console.error("error accessing object attr " + attr);
                }
            } else {
                // object with name field is a module, recursively invoke its functions.
                try {
                    tryInitModuleAttrs(mod[attr]);
                } catch (err) {
                    console.error("error accessing mod " + mod.name + " attr " + attr);
                }
            }
        } else if (ignoreSet.has(attrType)) {
            console.log("ignore attrType " + attrType);
        } else {
            console.error("unhandled attrType " + attrType);
        }
    }
}

function tryTriggerEvents(mod) {
    // The Node.js events module
    // https://www.w3schools.com/nodejs/ref_events.asp
    // https://nodejs.dev/the-nodejs-events-module
    console.log("checking events and listeners of " + mod.name + " and trying to trigger them!");
    var EventEmitter = require('events').EventEmitter;
    // FIXME: maybe add implementations to trigger the registered events
}


// Exit handler
// exit hook: https://github.com/sindresorhus/exit-hook
exitHook(() => {
    // FIXME: add exit handler to process remained modules
    console.log('Exiting');
});


function main() {
    // options
    var args = process.argv.slice(2);
    if (args.length !== 1) {
        console.log("Usage: " + process.argv[1] + " PKG_NAME");
        process.exit();
    }

    // import a module by its name
    var mod = require(args[0]);
    // tryTriggerEvents(mod);
    tryInitModuleAttrs(mod);
}


main();
