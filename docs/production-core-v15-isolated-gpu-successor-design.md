# V15 isolated GPU successor design

The V14 attempt `178c4bab01fcd9b259251930f45a3311506ba15689ba700492a103a2185ebd98`
is consumed terminal evidence. Its failure identity is
`f015000e13c2a3035b77a5c68cced755617407d1d4d0f84b67a3f9085e0c07b4`.
It accepted no rows or checkpoints. This design never resumes, retries, redraws,
or changes that attempt.

The V14 preflight checked `nvidia-smi -L` on the WSL host. The pinned runner
checks `torch.cuda.is_available()` inside an isolated namespace and chroot.
Those are distinct tests. The terminal journal recorded `frozen runtime
mismatch` and an NVML initialization warning. The pinned rootfs contains the
four required package versions. An isolated probe reproduced `cuInit(0) = 100`
(`CUDA_ERROR_NO_DEVICE`) and `torch.cuda.is_available() = false`, although
`/dev/dxg` was visible and `libcuda.so.1` loaded. The host WSL returned
`cuInit(0) = 0`.

The rootfs contains a frozen `/usr/lib/wsl/drivers` snapshot from a driver
directory no longer present on the reinstalled host. Diagnostic probes use a
temporary, read-only bind mount in a disposable namespace; they do not alter
the rootfs tar, host drivers, V14 attempt, or authority. Replacing only the
WSL `lib` directory kept `cuInit(0) = 100`. Replacing only the WSL `drivers`
directory changed `cuInit(0)` to `0`, device count to `1`, and PyTorch CUDA
availability to true. This identifies the stale embedded driver snapshot as
the sufficient cause in the tested isolation. The observation about the old
ComfyUI installation is context only; no CUDA Toolkit or ComfyUI installation
is required by this evidence.

`scripts/audit_production_core_successor_gpu_boundary_v15.py` validates the
published V14 source and terminal evidence, then runs the canonical isolated
probe and the controlled driver diagnostic. It records both results and a
content identity for the host driver directory. The audit can pass as a
**design audit** while execution readiness remains blocked: the canonical
rootfs still has no usable CUDA device in the runner isolation. No V15
execution authority, attempt, candidate output, adjudication, or promotion is
created by this design.

A future separately authorized successor boundary must specify and seal the
chosen driver exposure, verify its content and Linux-visible permissions,
run the CUDA probe in the exact production isolation before attempt
consumption, and bind the V14 terminal evidence. A host-only `nvidia-smi`
check is insufficient. Existing weights, V13 qualification generation,
schedule, and alias secret do not have a demonstrated dependency on this
driver exposure and are not changed here.

## Production driver snapshot and signed boundary

The production V15 snapshot is `/root/pf9-v15-wsl-drivers-snapshot` on native
ext4. It is a byte copy of the current host `/usr/lib/wsl/drivers`, with 2,310
regular files, no symlinks, and no writable entries. Its canonical manifest
identity is `f2074e618ba99a03e327ef2462a814b5a9503bbe5994692805ff8c4f11375126`.
The V15 shell verifies that manifest before and after mounting the snapshot
read-only over `/usr/lib/wsl/drivers` inside the isolated rootfs. It also pins
the snapshot's ext4 device/inode `2096:21113` and rechecks the manifest after
a runner exits. The V14 runner source remains byte-identical and preserves the V13 generation and
qualification identities. The rootfs archive itself remains byte-identical.

The production-snapshot probe uses the same mount, network and PID namespace,
chroot and Python runtime before any candidate could run. It observed
`cuInit(0) = 0`, one device and `torch.cuda.is_available() = true`. The
separate signed V15 authority binds that probe, the snapshot's manifest and
physical ext4 identity, the unchanged recovery and qualification identities,
the published V14 commit/tree, and the validated terminal V14 evidence. Its
status is zero new attempts, with candidate execution, adjudication and
promotion false. Signing this boundary does not authorize a new attempt.
