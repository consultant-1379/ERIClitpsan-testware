package com.ericsson.nms.litp.taf.test_cases;

/*------------------------------------------------------------------------------
 *******************************************************************************
 * COPYRIGHT Ericsson 2015
 *
 * The copyright to the computer program(s) herein is the property of
 * Ericsson Inc. The programs may be used and/or copied only with written
 * permission from Ericsson Inc. or in accordance with the terms and
 * conditions stipulated in the agreement/contract under which the
 * program(s) have been supplied.
 *******************************************************************************
 *----------------------------------------------------------------------------*/

import org.testng.annotations.*;
import utils.PtafTestRunner;
import com.ericsson.cifwk.taf.*;
import com.ericsson.cifwk.taf.annotations.*;



public class TestRunner2 extends PtafTestRunner {

	
	// Location of the python test scripts
	private String scriptsDir = "test_scripts/tst_litp_create_delete_snapshots";

	//Supply the csv containing the names of the python scripts to be copied to MS
	@DataDriven(name = "tst_litp_create_delete_snapshots")
	@Test
	@Context(context = { Context.CLI })
	public void run_scripts3(@TestId @Input("test_id") String test_id,
			@Input("vargs") String vargs) {
		executePythonScript(scriptsDir, test_id, vargs);
	}
	

}
