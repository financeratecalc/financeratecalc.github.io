-- FRC FHA Lender Denial Outlier Screen 2025 -- join examples
-- Model: frc-mix-expectation-v1.0
-- The screen is a screening signal, not evidence of misconduct or causation.

-- 1) Load the screen (adapt to your warehouse)
--    CSV: lender-outlier-screen-2025.csv
CREATE TABLE frc_outlier_screen_2025 (
  lei                                    VARCHAR(20) PRIMARY KEY,
  lender_name                            VARCHAR(200),
  apps_total_2025                        INTEGER,
  observed_denial_rate_pct               NUMERIC(5,2),
  expected_denial_rate_pct               NUMERIC(5,2),
  adjusted_ratio_observed_over_expected  NUMERIC(6,3),
  profile_coverage_pct                   NUMERIC(5,2),
  status                                 VARCHAR(48),
  model_version                          VARCHAR(32)
);

-- 2) Which of MY counterparties appear above model expectation?
SELECT c.seller_name,
       s.lei,
       s.apps_total_2025,
       s.observed_denial_rate_pct,
       s.expected_denial_rate_pct,
       s.adjusted_ratio_observed_over_expected AS ratio,
       s.profile_coverage_pct,
       s.status
FROM   my_counterparty_list c
JOIN   frc_outlier_screen_2025 s
  ON   s.lei = c.lei
WHERE  s.adjusted_ratio_observed_over_expected >= 1.5
  AND  s.status = 'screening_signal'      -- exclude thin-coverage rows
ORDER  BY ratio DESC;

-- 3) Coverage check first: which of my sellers cannot be screened at all?
SELECT c.seller_name, c.lei,
       COALESCE(s.status, 'not_in_screen') AS screen_status,
       s.profile_coverage_pct
FROM   my_counterparty_list c
LEFT   JOIN frc_outlier_screen_2025 s ON s.lei = c.lei
WHERE  s.lei IS NULL
   OR  s.status <> 'screening_signal';

-- 4) Portfolio view: exposure weighted by your own volume, not ours
SELECT SUM(p.upb) FILTER (WHERE s.adjusted_ratio_observed_over_expected >= 1.5
                            AND s.status = 'screening_signal') AS upb_above_expectation,
       SUM(p.upb) AS upb_total
FROM   my_positions p
JOIN   frc_outlier_screen_2025 s ON s.lei = p.seller_lei;

-- 5) Track a name over time once a second vintage is published
--    (previous versions stay online under their own model_version)
SELECT lei, model_version, observed_denial_rate_pct,
       expected_denial_rate_pct, adjusted_ratio_observed_over_expected
FROM   frc_outlier_screen_all_vintages
WHERE  lei = :lei_of_interest
ORDER  BY model_version;
