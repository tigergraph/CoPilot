import { Counter } from 'k6/metrics';
export const failedReqCounter = new Counter('Failed_Requests');
export const okReqCounter = new Counter('OK_Requests');
export const qAnsweredCounter = new Counter('Questions_Answered');

