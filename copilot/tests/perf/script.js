import http from "k6/http";
import encoding from "k6/encoding";
import { check, sleep } from "k6";
import {
  failedReqCounter,
  okReqCounter,
  qAnsweredCounter,
} from "./customMetrics.js";

const copilot = `${cfg.copilotURL}`;
const cfg = JSON.parse(open("config.json"));
export const options = {
  vus: cfg.VuCount,
  duration: cfg.duration,
};

/*
 * Test that the API is up and creds are correct
 */
export function setup() {
  const creds = encoding.b64encode(`${cfg.username}:${cfg.password}`);
  const opts = {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Basic ${creds}`,
    },
  };

  console.log("login...");
  const res = http.post(copilot + `/${cfg.graphName}/login`, null, opts);
  if (res.status === 401) {
    throw Error("bad credenials");
  }

  return opts;
}

/*
 * The function that defines VU logic.
 */
export default function (opts) {
  const body = { query: "How many pods do we have?" };
  const resp = http.post(
    copilot + "/DigitalInfra/query",
    JSON.stringify(body),
    opts,
  );

  // was the request ok
  const statOk = resp.status === 200;
  if (statOk) {
    okReqCounter.add(1);
  } else {
    failedReqCounter.add(1);
  }

  // did copilot answer the question?
  const qAnswered = resp.json()["answered_question"];
  if (qAnswered) {
    qAnsweredCounter.add(1)
  }
  console.log("qans= ", qAnswered, qAnswered === true, typeof qAnswered);

  check(resp, {
    "status 200": () => statOk,
    "Question was answered": () => qAnswered,
  });
  sleep(1);
}

export function teardown() {
  console.log("done...");
}
