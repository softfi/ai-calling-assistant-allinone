# S1-T1 — India telephony provider matrix

Researched 2026-11-20 from official provider docs only (links per row). Prices exclude 18% GST and
are list prices as published on that date; confirm with sales before committing. Not verified by a
sales call yet (S1 task text asks for one — do it with the top-1 provider during S1-T3).

## Hard constraints that decide the shortlist
- **Media must stay in India.** TRAI rules require India calls to be anchored on servers in India;
  Plivo fails calls with `violates_media_anchoring` / hangup 4590 when the SIP endpoint is outside
  India ([Plivo: calling in India via SIP][plivo-sip-in]). → LiveKit project must be region-pinned
  to India, using the `*.india.sip.livekit.cloud` endpoint ([LiveKit region pinning][lk-pin]).
  LiveKit notes that a pinned India region cannot fail over: during the 2026-06-02 incident India
  SIP traffic went to Dubai and outbound calls to Indian numbers were rejected ([status][lk-incident]).
- **Only India-registered businesses with KYC** can rent Indian numbers for domestic calling
  (Plivo, Exotel). Twilio sells only +91 800 toll-free numbers to a non-Indian address and outbound
  calls to India must come from non-Indian numbers ([Twilio IN voice][tw-voice],
  [Twilio IN regulatory][tw-reg]) → **Twilio is out** for domestic inbound + callbacks.
- **Number series:** landline series (e.g. 022/080) = service & transactional calls only;
  140-series = promotional only; 160-series = BFSI only. Cold calling prohibited; commercial calls
  need explicit digital consent or they count as UCC ([Plivo India FAQ][plivo-faq]). Our MVP
  (inbound + callbacks to leads who enquired) fits a landline-series number.

## Matrix
| | **Plivo** | **Exotel** | **Twilio** | Others (Tata Tele, Airtel, Vobiz…) |
|---|---|---|---|---|
| Licence / role | CPaaS, India data region (Mumbai) | UL-VNO (licensed) ([Exotel ref. arch][ex-arch]) | Global CPaaS | Tata Tele/Airtel = licensed operators; Vobiz licence not confirmed |
| Indian inbound numbers | Yes, landline series (022/080…), 140, 160 ([Plivo rent IN][plivo-rent]) | Yes, ExoPhones (landline, mobile-series, toll-free) ([ExoPhone][ex-num]) | Toll-free +91 800 only | Enterprise contracts |
| KYC | Any one of GST cert / COI / Udyam (PAN alone not accepted), signed & sealed; India data-region account; review ~5 min for 022/080 ([Plivo rent IN][plivo-rent]) | COI + GST + PAN + signatory ID (Pvt Ltd/LLP), business address proof < 3 months; 1–3 business days ([Exotel KYC][ex-kyc]) | N/A for domestic | Enterprise KYC + contract |
| ₹/min inbound / outbound | **₹0.38 / ₹0.38** domestic, Voice API and SIP trunking alike ([voice][plivo-price], [SIP][plivo-sip-price]) | Not published; quote/calculator only ([Exotel pricing FAQ][ex-price]) | — | Quote |
| Pulse | **30 s** | Per plan: per-second after minimum, or per-pulse (often 60 s) ([Exotel pricing FAQ][ex-price]) | — | Quote |
| Number rental | ₹200/month | Activation fee + monthly rental, amount not published | — | Quote |
| Into LiveKit | **SIP trunk** inbound + outbound; LiveKit quickstart; needs LiveKit India region pinning ([Plivo SIP IN][plivo-sip-in]). Audio streaming (WebSocket) also included free | **SIP trunk** (vSIP/ExoTrunk; TLS 443 + SRTP, IP allowlist or digest auth, 200 CPM default) ([Exotel ↔ LiveKit][ex-lk], [TLS guide][ex-tls]); or **Voicebot applet** bidirectional WebSocket (Beta) ([Voicebot][ex-vb]) | SIP into LiveKit possible but no Indian domestic numbers | BYO SIP; a LiveKit community report of outbound to Tata Smartflo never connecting ([thread][lk-tata]) |
| Human-first ring | Voice API `<Dial>` with timeout, or do it in LiveKit (outbound leg to agent's phone) | Connect applet (dial whom, dynamic URL); ring-time setting for the applet not documented ([Connect dynamic URL][ex-connect]) | — | — |
| Transfer to human | LiveKit **warm transfer needs only an outbound trunk** (agent dials human with `CreateSIPParticipant`, then moves them in) ([LiveKit warm transfer][lk-warm]); cold transfer = SIP REFER — Plivo REFER support not documented → verify | Same LiveKit warm transfer over ExoTrunk; REFER not documented → verify | — | — |
| Recording | ₹0/min, storage free 90 days ([voice][plivo-price]) | Available; price not published | — | — |
| Webhooks | Answer/hangup/callback URLs (Voice API) | Passthru applet + StatusCallback | — | — |
| Extras | Noise cancellation ₹0.12/min, transcription ₹0.81/min | Startup credits offers | — | — |

## Verdict
**Plivo (SIP trunk → LiveKit India) is top-1 for S1-T3**: published INR rates, 30-s pulse, KYC with
a single business document reviewed in minutes, documented LiveKit path. **Exotel is the fallback**
(licensed VNO, also documents LiveKit SIP, but pricing and KYC turnaround need a sales call).
Twilio is not viable for domestic Indian numbers.

[plivo-sip-in]: https://www.plivo.com/docs/voice-agents/sip-trunking/deploy/calling-in-india
[plivo-rent]: https://www.plivo.com/docs/numbers/rent-india-numbers
[plivo-faq]: https://plivo.com/docs/faq/voice-api-and-SIP-trunking/india-calling
[plivo-price]: https://www.plivo.com/voice/pricing/in/
[plivo-sip-price]: https://www.plivo.com/sip-trunking/pricing/in/
[ex-arch]: https://exotel.com/blog/production-architecture-low-latency-voice-ai-exotel-livekit/
[ex-num]: https://developer.exotel.com/docs/call-support/basics/virtual-numbers
[ex-kyc]: https://developer.exotel.com/docs/getting-started/kyc-verification
[ex-price]: https://developer.exotel.com/docs/faqs/pricing-plans
[ex-lk]: https://support.exotel.com/support/solutions/articles/3000134145-livekit-and-exotel-sip-trunking-integration-guide
[ex-tls]: https://developer.exotel.com/docs/sip-trunking/tls-integration
[ex-vb]: https://docs.exotel.com/exotel-agentstream/voicebot-applet
[ex-connect]: https://docs.exotel.com/voice-apis/programmable-connect-working-with-connect-applet-dynamic-url
[tw-voice]: https://www.twilio.com/en-us/guidelines/in/voice
[tw-reg]: https://www.twilio.com/en-us/guidelines/in/regulatory
[lk-pin]: https://docs.livekit.io/telephony/features/region-pinning/
[lk-warm]: https://docs.livekit.io/telephony/features/transfers/warm
[lk-incident]: https://status.livekit.io/incidents/616ks8lp2mm2
[lk-tata]: https://community.livekit.io/t/outbound-byo-sip-trunk-to-an-indian-carrier-fails-with-a-raw-tcp-connect-timeout/1887
