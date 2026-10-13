"""Bounded historical cleanup authorized by Sergei on 2026-10-13.

No source/recovery retirement. Plan uses a caller-supplied SQLite backup; apply
requires exclusive existing app catalog ownership and an unchanged native plan.
"""
import argparse,hashlib,json,sqlite3
from pathlib import Path
from contextlib import closing
from app import catalog_lock
from scanner import DEFAULT_ROOTS
from storage_cleanup import StorageCleanup
from native_io import BoundaryError,ordinary

APPROVED_JOBS=(
 '846deacf-5048-4a45-a762-d4d4cd891602',
 'a8ab6b6b-102a-4459-b769-522254ac52e0',
 '4db85341-6278-4571-ae2a-11ddebff442f',
 'a8d51f2c-3b13-49a4-8aa3-9085bf62d910',
 '3b299c69-3390-4d3f-a0b6-a9ce1cbcc75c',
 'b324a55e-0eab-42ce-a529-262796c9bcee',
 '71c8534e-08b4-47b1-8f11-3b6fab44c6ed',
 'b55f0216-2c84-49a6-981f-6520f711f014')
APPROVED_BYTES=119317276892
OBSERVED_COUNT=136  # 2026-10-13 backup + exact C-only receipt-name inventory.

def records(database):
 with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
  db.execute('PRAGMA query_only=ON')
  return [list(db.execute('SELECT job_id,state,manifest_hash,manifest,output FROM audio_jobs WHERE job_id=?',(job,)).fetchone() or ()) for job in APPROVED_JOBS]

def build_plan(storage):
 jobs=[storage.working_files(job,dry_run=True,normalized_only=True) for job in APPROVED_JOBS]
 count=sum(len(job['files']) for job in jobs);size=sum(job['bytes'] for job in jobs)
 if (count,size)!=(OBSERVED_COUNT,APPROVED_BYTES):raise BoundaryError('Approved historical working inventory changed; preserve and review')
 return {'jobs':jobs,'count':count,'bytes':size}

def remaining_plan(storage, job):
 remaining=[]
 for item in job['files']:
  path=ordinary(item['path'])
  if path.exists():remaining.append(item);continue
  receipt=storage._known(path)
  if not receipt or receipt['job_id']!=job['job_id'] or receipt['kind']!='staging' or receipt['state'] not in {'removed','absent_after_intent','removal_intended','disposition_set'} or (receipt['sha256'],receipt['size'])!=(item['sha256'],item['size']) or json.loads(receipt['facts'])!=item['facts']:
   raise BoundaryError('Absent working name lacks exact frozen-plan removal proof')
 return remaining

def validate_frozen_plan(storage, expected):
 if tuple(job['job_id'] for job in expected['jobs'])!=APPROVED_JOBS or (expected['count'],expected['bytes'])!=(OBSERVED_COUNT,APPROVED_BYTES):
  raise BoundaryError('Frozen approval scope changed')
 if sum(len(job['files']) for job in expected['jobs'])!=OBSERVED_COUNT or sum(item['size'] for job in expected['jobs'] for item in job['files'])!=APPROVED_BYTES:
  raise BoundaryError('Frozen approval totals changed')
 remaining=[]
 for job in expected['jobs']:
  wanted=remaining_plan(storage,job)
  actual=storage.working_files(job['job_id'],dry_run=True,normalized_only=True)
  if actual['files']!=wanted or actual['output_sha256']!=job['output_sha256']:
   raise BoundaryError('Native working inventory changed; preserved')
  remaining.append(wanted)
 return remaining

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('mode',choices=('plan','apply'))
 parser.add_argument('--data-root',required=True)
 parser.add_argument('--catalog-copy',required=True)
 parser.add_argument('--plan',required=True)
 parser.add_argument('--plan-sha256')
 args=parser.parse_args();data=ordinary(args.data_root);copy=ordinary(args.catalog_copy);plan_path=ordinary(args.plan)
 if copy.is_relative_to(data) or plan_path.is_relative_to(data):raise BoundaryError('Keep backup/plan outside live data')
 database=data/'inventory.sqlite3';stage=data/'merge-cache'/'audio-staging';recovery=data/'source-recovery'
 if args.mode=='plan':
  source=records(copy)
  storage=StorageCleanup(copy,stage,recovery)
  plan=build_plan(storage);plan['records_sha256']=hashlib.sha256(json.dumps(source,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  raw=json.dumps(plan,ensure_ascii=False,sort_keys=True,indent=2).encode()
  with open(plan_path,'xb') as stream:stream.write(raw)
  print(json.dumps({'count':plan['count'],'bytes':plan['bytes'],'plan_sha256':hashlib.sha256(raw).hexdigest()}))
 else:
  raw=plan_path.read_bytes()
  if not args.plan_sha256 or hashlib.sha256(raw).hexdigest()!=args.plan_sha256:raise BoundaryError('Exact reviewed plan SHA-256 is required')
  expected=json.loads(raw)
  # A paused GUI still owns this lock. Apply waits for a supported idle shutdown;
  # no process termination, Stop/Start, HTTP POST or lock bypass is performed.
  with catalog_lock(database,DEFAULT_ROOTS):
   current=records(database)
   if hashlib.sha256(json.dumps(current,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()!=expected['records_sha256']:
    raise BoundaryError('Published catalog proof changed; preserved')
   storage=StorageCleanup(database,stage,recovery)
   remaining=validate_frozen_plan(storage,expected)
   removed=[]
   for job,wanted in zip(expected['jobs'],remaining):
    removed.append(storage.working_files(job['job_id'],normalized_only=True,expected_plan=wanted))
   if records(database)!=current:raise BoundaryError('Protected publication records changed')
   print(json.dumps({'removed_count':sum(len(job['files']) for job in removed),'removed_bytes':sum(job['bytes'] for job in removed),'approved_total_bytes':APPROVED_BYTES,'approved_total_count':OBSERVED_COUNT}))

if __name__=='__main__':main()
