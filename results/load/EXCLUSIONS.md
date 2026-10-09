# Load-test runs excluded from the analysis

A run is listed here only when it is left out of the pooled results. Its folder is kept unchanged as evidence.

## load-r2-qwen2.5-7b-r3 (R2, qwen2.5:7b, run 3 of 3): excluded; replaced by run 4

* **What happened:** JMeter reported 1 error in 55 requests (1.82%). The failed request is the last ticket of the run
  (sequence number 55, row 4054) with `java.net.SocketException: Socket closed`.
* **Cause:** the 30-minute arrival schedule ended while that ticket was still being classified by the 7B model
  (service time 10–25 s). JMeter then interrupted the request, as its own log states: *"Test schedule finished,
  however, there are 1 thread(s) still running. Will interrupt the threads."* The request ended at timestamp
  1791523331169, 1 ms before JMeter's "Tidying up" at 1791523331170.
* **Service side:** the service log shows all 56 tickets of that run (55 from JMeter plus the warm-up) with status 201,
  so the service did not fail; the response was cut off on the client side.
* **Scope:** this message appears in no other run's `jmeter.log`; all other runs completed every request.
* **Fix:** the test plan now ends each schedule with a drain pause (`pause(2 min)` for the mixed and R2 tests,
  `pause(12 min)` for the stress test) so outstanding requests can finish. The R2 run was repeated as run 4
  (`load-r2-qwen2.5-7b-r4`); the R2 verdict uses runs 1, 2 and 4.
* **Why a new run id:** run ids are never reused, and the original folder is kept as it was.
