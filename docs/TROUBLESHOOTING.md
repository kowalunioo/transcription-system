# Troubleshooting

## `GROQ_API_KEY` missing
Make sure the variable is visible to the OpenClaw gateway/runtime, then restart the gateway.

## Groq returns 403 or WAF-like errors
Test the same key with `curl` from the same machine. If `curl` works but your custom client does not, prefer the built-in curl-based backend.

## `curl` not found
Install curl and make sure it is on `PATH`.

## Repeated retranscription
The system caches by file fingerprint + settings. If you want a fresh run, disable cache or change output target.

## Diarization
Not implemented yet in the Groq-only backend.
