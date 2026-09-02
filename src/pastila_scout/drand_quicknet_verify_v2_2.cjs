"use strict";

// Offline-only adapter around the pinned official drand-client distribution.
// Input is one JSON object on stdin. No URL or transport is accepted.
const fs = require("fs");
const path = require("path");

const QUICKNET_HASH = "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971";
const QUICKNET_PUBLIC_KEY = "83cf0f2896adee7eb8b5f01fcad3912212c437e0073e911fb90022d3e760183c8c4b450b6a0a6c3ac6a5776a2d1064510d1fec758c921cc22b0e17e63aaf4bcb5ed66304de9cf809bd274ca73bab4af5a6e9c76a4bc09e76eae8991ef5ece45a";
const QUICKNET_GROUP_HASH = "f477d5c89f21a17c863a7f937c6a6d15859414d2be09cd448d4279af331c5d3e";
globalThis.fetch = async () => { throw new Error("network transport prohibited"); };

async function main() {
  const root = process.env.PASTILA_DRAND_CLIENT_ROOT;
  if (!root) throw new Error("pinned drand-client root missing");
  const client = require(path.join(root, "build", "cjs", "index.cjs"));
  const request = JSON.parse(fs.readFileSync(0, "utf8"));
  if (Object.keys(request).sort().join(",") !== "beacon,chain_info,expected_round") {
    throw new Error("request schema mismatch");
  }
  const info = request.chain_info;
  if (info.hash !== QUICKNET_HASH || info.public_key !== QUICKNET_PUBLIC_KEY ||
      info.groupHash !== QUICKNET_GROUP_HASH || info.period !== 3 ||
      info.genesis_time !== 1692803367 || info.schemeID !== "bls-unchained-g1-rfc9380" ||
      info.metadata?.beaconID !== "quicknet") {
    throw new Error("Quicknet identity mismatch");
  }
  if (!Number.isSafeInteger(request.expected_round) || request.expected_round < 1 ||
      request.beacon.round !== request.expected_round) {
    throw new Error("round mismatch");
  }
  const local = {
    options: {disableBeaconVerification: false, noCache: false},
    get: async (round) => {
      if (round !== request.expected_round) throw new Error("unexpected round request");
      return request.beacon;
    },
    latest: async () => { throw new Error("latest is prohibited"); },
    chain: () => ({baseUrl: "offline://pinned-quicknet", info: async () => info})
  };
  await client.fetchBeacon(local, request.expected_round);
  process.stdout.write("PASS_QUICKNET_BLS\n");
}

main().catch((error) => {
  process.stderr.write(`FAIL_CLOSED: ${error.message}\n`);
  process.exitCode = 1;
});
