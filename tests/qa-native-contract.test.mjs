import test from 'node:test';
import {runPureChecks} from '../scripts/qa-native/pure-checks.mjs';
test('fixed protected Books contracts and fail-closed orchestration',async()=>{await runPureChecks();});
import {engineeringOwnerChecks} from '../scripts/qa-native/engineering-owner-checks.mjs';
test('engineering identity and joint closure source contracts with pure native fakes',async()=>{await engineeringOwnerChecks();});
import {nativeFixturePlanChecks} from '../scripts/qa-native/native-fixture-plan-checks.mjs';
test('finite native fixture source and plan contracts without native execution',async()=>{await nativeFixturePlanChecks();});
import {diagnosticCaptureChecks} from '../scripts/qa-native/diagnostic-capture-checks.mjs';
test('bounded nonauthoritative diagnostic capture with pure native journal faults',async()=>{await diagnosticCaptureChecks();});

import {ownerIdPlanChecks} from '../scripts/qa-native/fixture-owner-ids-checks.mjs';
test('plan-bound four inner owner labels and preparation provenance with pure fakes',async()=>{await ownerIdPlanChecks();});

import {engineeringTerminalChecks} from '../scripts/qa-native/engineering-terminal-checks.mjs';
test('opaque retained terminal object proof and strict native-v2 schema with pure fakes',async()=>{await engineeringTerminalChecks();});
