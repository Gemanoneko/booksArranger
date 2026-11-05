from pathlib import Path
text=Path(__file__).with_name('freeze-names-r2.py').read_text(encoding='utf-8')
text=text.replace('names-backend-stage-r2','names-backend-stage-r3').replace('freeze-names-r2.py','freeze-names-r3.py')
text=text.replace("'names-backend-liveness-cohort'):","'names-backend-liveness-cohort','names-startup-red','names-startup-green','names-r3-cohort'):")
text=text.replace("'results':'39/39 ledger", "'results':'40/40 ledger")
text=text.replace('PASS8.822s(owned9.576s)', 'PASS9.335s(owned10.182s)')
text=text.replace('DecisionRuntime recovers accepted names at service start;', 'DecisionRuntime is constructed inert and starts as the final constructor operation, after every progress callback and completed-task enrollment. Actual BrowserServer._open_merge cancellation regression failed before correction (orphan non-daemon owner) and passed after it, preserving the accepted intent without starting any owner before constructor return. Normal HTTP/restart companion passed. DecisionRuntime recovers accepted names at service start;')
exec(compile(text,str(__file__),'exec'))
