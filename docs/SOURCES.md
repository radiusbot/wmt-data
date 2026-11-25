# Indian Railways data sources: findings

Researched 2026-11-25 while wmt-data was still planned as a timetable crawler.
That plan was dropped the same day (see the decision at the end). These notes stay
because the app now reads the same public pages directly from the user's phone.

## NTES (National Train Enquiry System, run by CRIS)

Base: `https://enquiry.indianrail.gov.in/mntes/`. Public, no login, and no captcha
on any of the surfaces below.

| Surface | What it returns |
|---|---|
| `GET javascripts/train_data.js` | `var arrTrainList = ["12627- KARNATAKA EXP", …]`. About 11,389 entries on 2026-11-25. |
| `GET javascripts/station_data.js` | `var arrStationList = [{"code":"SBC","name":"…"}, …]`. About 8,771 stations. |
| `GET GetCSRFToken` | `["<field name>", "<value>"]`. Single use and bound to the session cookie. |
| `POST q?opt=TrainServiceSchedule&subOpt=show&trainNo=<n>` (form: `lan=en`, `trainNo`, CSRF field) | HTML schedule page: stops, arrival and departure, day offset, distance, days of run. |
| `GET disclaimerDisplay.html` | Terms and conditions (quoted below). |

Observed behaviour:

* A CSRF token that has already been used returns an **empty 200 body**, not an error.
  Clients must fetch a new token for every schedule POST.
* Schedule pages mark the origin and destination with `SRC` / `DSTN` in place of times.
* `https://enquiry.indianrail.gov.in/ntes/` (the old desktop site) only redirects to `/mntes`
  through JavaScript, and contains a hidden "site unavailable" message that is turned on during maintenance.
* The `mntes` home page loads Google Analytics and Google Publisher Tag ads.
* Two trains in the test set, 12839 and 12840 (Howrah to Chennai Mail), returned no schedule during the
  trial fetch. NTES does not always have a schedule for every number in its own train list.

## indianrail.gov.in (Passenger Reservation Enquiry)

The train schedule enquiry on `www.indianrail.gov.in/enquiry/` puts a **captcha question** in
front of results. It was therefore never used as a source for automated fetching.

## Trial fetch (deleted)

On 2026-11-25 a sample of 34 train numbers was fetched from NTES. The crawler allowed at most 2 sessions
and waited at least 1.5 s between requests. 32 schedules were fetched and 2 failed (12839 and 12840).
Those cached schedules were used for only one thing: checking the train numbers behind
the nicknames in `app/assets/config/train_aliases.json`. All crawl output has been deleted.

## Decision 2026-11-25: no published timetable

The owner read the NTES terms and decided:
**the app is phone-only, and no timetable database is published.** The phone fetches NTES's public lists
and schedules itself, the same way a browser on that phone would. wmt-data does not crawl, build or
publish any railway data. It hosts only static pages and two small config files.

Clauses from `https://enquiry.indianrail.gov.in/mntes/disclaimerDisplay.html`, captured 2026-11-25
(copy in `the private app repository at docs/evidence/ntes_terms_disclaimer_2026-11-25.html; not republished here, per those same terms`,
sha256 `ad4dc5ebb53fd6d4a35d4933bc04087dd81c2650bf393f602a41067097c2dd47`):

> **LIMITED PERMISSION TO COPY:**
> You are permitted to print or download extracts from these pages for your personal use only. Any copies
> of these pages saved to disk or to any other storage medium may only be used for subsequent viewing
> purposes or to print extracts for personal use. You may not (whether directly or through the use of any
> software program) create a database in electronic or structured manual form by regularly or
> systematically downloading and storing all or any part of the pages from this site. No part of The Site
> may be reproduced or transmitted to or stored in any other web site, nor may any of its pages or part
> thereof be disseminated in any electronic or non electronic form, nor included in any public or private
> electronic retrieval system or service without Government of India, Ministry of Railway's prior written
> permission.

> **COMMERCIAL USE:**
> The Railway related data available on this site should not be used for commercial purpose.

> **COPYRIGHT POLICY:**
> Material featured on this Website may be reproduced free of charge after taking proper permission by
> sending a mail to us. However, the material has to be reproduced accurately and not to be used in a
> derogatory manner or in a misleading context. Wherever the material is being published or issued to
> others, the source must be prominently acknowledged.

> **DISCLAIMER:** […] The information is presented on best-effort basis. While we continually try to
> improve its reliability and accuracy, passengers are advised to verify the information from the
> concerned railway station or local, authorized railway sources, as necessary.

> **LINKS TO TRAIN ENQUIRY BY OTHER WEBSITES-**
> We do not object to you linking directly to the information that is hosted on this Website and no prior
> permission is required for the same. […] Also, we do not permit our pages to be loaded into frames on
> your site.

How each clause applies:

* A crawled, published timetable is exactly "a database … by regularly or systematically downloading and
  storing" pages that is then "transmitted to or stored in any other web site". So it was dropped.
* Reading pages on the user's phone on demand is closer to the personal-use permission, but it is
  **not cleared**. The "commercial purpose" clause still applies to an app that shows ads. This is
  open item H1 in `owner_action.md` (legal review). The remote `config.json` can switch off each source
  without an app update.
* Every screen that shows railway data should cite the source, and should say that times are best effort
  and must be checked at the station.
