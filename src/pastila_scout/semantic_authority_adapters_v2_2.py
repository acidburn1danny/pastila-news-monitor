"""Production-shaped, network-free V2.2 metadata and verifier adapters."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import hashlib, json, re, subprocess, tempfile
from pathlib import Path
from typing import BinaryIO, Iterable, Mapping, Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

HEX64=set("0123456789abcdef")
def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def canonical(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v:object)->bool:return isinstance(v,str) and len(v)==64 and set(v)<=HEX64

@dataclass(frozen=True)
class ObjectSpec:
 locator:str; byte_length:int; record_count:int|None=None

def parse_openalex_manifest(raw:bytes,*,base_prefix:str="s3://openalex/data/jsonl/")->tuple[date,tuple[ObjectSpec,...]]:
 """Parse the documented combined/per-entity OpenAlex manifest without fetching objects."""
 try:value=json.loads(raw)
 except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise ValueError("OpenAlex manifest is not UTF-8 JSON") from exc
 if not isinstance(value,dict) or not isinstance(value.get("date"),str):raise ValueError("OpenAlex manifest date missing")
 try:released=date.fromisoformat(value["date"])
 except ValueError as exc:raise ValueError("OpenAlex manifest date invalid") from exc
 files=value.get("files")
 if files is None and isinstance(value.get("entities"),list):
  files=[item for entity in value["entities"] if isinstance(entity,dict) for item in entity.get("files",[])]
 if not isinstance(files,list) or not files:raise ValueError("OpenAlex manifest files missing")
 output=[];seen=set()
 for item in files:
  if not isinstance(item,dict) or set(item)!={"url","meta"}:raise ValueError("OpenAlex file schema mismatch")
  url,meta=item["url"],item["meta"]
  if not isinstance(url,str) or not url.startswith(base_prefix) or url in seen:raise ValueError("OpenAlex locator invalid or duplicate")
  if not isinstance(meta,dict) or not isinstance(meta.get("content_length"),int) or meta["content_length"]<=0:raise ValueError("OpenAlex length invalid")
  count=meta.get("record_count")
  if count is not None and (not isinstance(count,int) or count<0):raise ValueError("OpenAlex record count invalid")
  seen.add(url);output.append(ObjectSpec(url,meta["content_length"],count))
 if isinstance(value.get("record_count"),int) and all(x.record_count is not None for x in output) and sum(x.record_count or 0 for x in output)!=value["record_count"]:raise ValueError("OpenAlex record count closure failure")
 if isinstance(value.get("content_length"),int) and sum(x.byte_length for x in output)!=value["content_length"]:raise ValueError("OpenAlex byte length closure failure")
 return released,tuple(sorted(output,key=lambda x:x.locator.encode()))

def bind_s3_versions(specs:Iterable[ObjectSpec],version_ids:Mapping[str,str])->tuple[ObjectSpec,...]:
 """Turn mutable manifest keys into immutable S3 version locators with exact closure."""
 specs=tuple(specs)
 if set(version_ids)!={s.locator for s in specs}:raise ValueError("S3 version identity closure failure")
 output=[]
 for spec in specs:
  version=version_ids[spec.locator]
  if not isinstance(version,str) or not version or any(c.isspace() for c in version):raise ValueError("S3 version identity invalid")
  parts=urlsplit(spec.locator);query=parse_qs(parts.query,keep_blank_values=True)
  if "versionId" in query:raise ValueError("S3 locator already versioned")
  query["versionId"]=[version]
  output.append(ObjectSpec(urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query,doseq=True),parts.fragment)),spec.byte_length,spec.record_count))
 return tuple(output)

def parse_crossref_release_descriptor(raw:bytes,*,verified_official_capture_sha256:str)->tuple[date,tuple[ObjectSpec,...]]:
 """Parse a frozen adapter descriptor derived only from Crossref's official release record."""
 try:value=json.loads(raw)
 except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise ValueError("Crossref descriptor is not UTF-8 JSON") from exc
 if set(value)!={"publisher","release_date","official_release_url","official_release_record_sha256","objects"} or value["publisher"]!="Crossref":raise ValueError("Crossref descriptor schema mismatch")
 if value["official_release_record_sha256"]!=verified_official_capture_sha256 or not _sha(verified_official_capture_sha256):raise ValueError("Crossref release capture not verified")
 try:released=date.fromisoformat(value["release_date"])
 except ValueError as exc:raise ValueError("Crossref release date invalid") from exc
 if not str(value["official_release_url"]).startswith("https://www.crossref.org/"):raise ValueError("Crossref release authority mismatch")
 objects=value["objects"]
 if not isinstance(objects,list) or not objects:raise ValueError("Crossref objects missing")
 result=[];seen=set()
 for item in objects:
  if set(item)!={"versioned_locator","byte_length"}:raise ValueError("Crossref object schema mismatch")
  locator=item["versioned_locator"]
  if not isinstance(locator,str) or not locator.startswith(("s3://","https://academictorrents.com/")) or locator in seen:raise ValueError("Crossref locator invalid")
  if not isinstance(item["byte_length"],int) or item["byte_length"]<=0:raise ValueError("Crossref length invalid")
  seen.add(locator);result.append(ObjectSpec(locator,item["byte_length"]))
 return released,tuple(sorted(result,key=lambda x:x.locator.encode()))

def hash_object(stream:BinaryIO,*,expected_length:int,chunk_size:int=1<<20)->tuple[str,int]:
 if expected_length<=0 or chunk_size<=0:raise ValueError("hash parameters invalid")
 h=hashlib.sha256();total=0
 while True:
  block=stream.read(chunk_size)
  if not block:break
  if not isinstance(block,bytes):raise ValueError("binary stream required")
  total+=len(block);h.update(block)
 if total!=expected_length:raise ValueError("object length mismatch")
 return h.hexdigest(),total

def commitment(specs:Iterable[ObjectSpec],observed:Mapping[str,tuple[str,int]])->dict[str,Any]:
 specs=tuple(specs)
 if len({s.locator for s in specs})!=len(specs):raise ValueError("duplicate manifest locator")
 if any(not _immutable_locator(s.locator) for s in specs):raise ValueError("unversioned locator prohibited")
 if set(observed)!={s.locator for s in specs}:raise ValueError("manifest object-set closure failure")
 leaves=[]
 for spec in sorted(specs,key=lambda x:x.locator.encode()):
  sha256,length=observed[spec.locator]
  if not _sha(sha256) or isinstance(length,bool) or not isinstance(length,int) or length!=spec.byte_length:raise ValueError("object commitment mismatch")
  leaf={"VERSIONED_IMMUTABLE_LOCATOR":spec.locator,"BYTE_LENGTH":length,"SHA256":sha256}
  leaves.append((leaf,hashlib.sha256(b"\0"+canonical(leaf)).digest()))
 nodes=[x[1] for x in leaves]
 while len(nodes)>1:nodes=[hashlib.sha256(b"\1"+nodes[i]+(nodes[i+1] if i+1<len(nodes) else nodes[i])).digest() for i in range(0,len(nodes),2)]
 root=(nodes[0] if nodes else hashlib.sha256(b"").digest()).hex()
 return {"leaves":[x[0] for x in leaves],"object_count":len(leaves),"total_bytes":sum(x[0]["BYTE_LENGTH"] for x in leaves),"merkle_root":root}

def _immutable_locator(locator:str)->bool:
 parts=urlsplit(locator);query=parse_qs(parts.query,keep_blank_values=True)
 versions=query.get("versionId",[]);infohashes=query.get("infohash",[])
 return (len(versions)==1 and bool(versions[0])) or (len(infohashes)==1 and bool(re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}",infohashes[0])))

def verify_rfc3161(*,payload:bytes,receipt:bytes,openssl:Path,ca_file:Path,expected_executable_sha256:str,expected_ca_sha256:str,expected_timestamp_utc:str)->None:
 if digest(openssl.read_bytes())!=expected_executable_sha256:raise ValueError("OpenSSL executable identity mismatch")
 if digest(ca_file.read_bytes())!=expected_ca_sha256:raise ValueError("CA bundle identity mismatch")
 with tempfile.TemporaryDirectory() as folder:
  p=Path(folder);(p/"payload").write_bytes(payload);(p/"receipt").write_bytes(receipt)
  run=subprocess.run([str(openssl),"ts","-verify","-data",str(p/"payload"),"-in",str(p/"receipt"),"-CAfile",str(ca_file)],capture_output=True,timeout=30,check=False)
  inspect=subprocess.run([str(openssl),"ts","-reply","-in",str(p/"receipt"),"-text"],capture_output=True,timeout=30,check=False)
 if run.returncode or b"Verification: OK" not in run.stdout+run.stderr:raise ValueError("RFC3161 verification failed")
 text=(inspect.stdout+inspect.stderr).decode("utf-8","replace")
 from email.utils import parsedate_to_datetime
 match=re.search(r"Time stamp: (.+)",text)
 if inspect.returncode or "Hash Algorithm: sha256" not in text:raise ValueError("RFC3161 algorithm mismatch")
 if not match or parsedate_to_datetime(match.group(1)).strftime("%Y-%m-%dT%H:%M:%SZ")!=expected_timestamp_utc:raise ValueError("RFC3161 timestamp mismatch")

def verify_with_pinned_executable(*,executable:Path,expected_sha256:str,args:list[str],expected_stdout:bytes,input_bytes:bytes=b"")->bytes:
 """Fail-closed boundary for real Rekor/drand cryptographic clients."""
 if digest(executable.read_bytes())!=expected_sha256:raise ValueError("verifier executable identity mismatch")
 run=subprocess.run([str(executable),*args],input=input_bytes,capture_output=True,timeout=30,check=False)
 if run.returncode or run.stdout.strip()!=expected_stdout or run.stderr:raise ValueError("external cryptographic verification failed")
 return run.stdout

def verify_quorum_payloads(payloads:Mapping[str,bytes],*,expected_endpoints:frozenset[str],minimum:int=2)->bytes:
 if minimum<2 or set(payloads)!=set(expected_endpoints) or len(payloads)<minimum or any(not key.startswith("https://") for key in payloads):raise ValueError("endpoint quorum invalid")
 values=set(payloads.values())
 if len(values)!=1:raise ValueError("endpoint quorum mismatch")
 return next(iter(values))
