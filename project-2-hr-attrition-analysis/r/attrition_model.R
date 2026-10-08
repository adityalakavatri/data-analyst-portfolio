# =====================================================================
# attrition_model.R  -  Statistical modelling in R (companion to python/analysis.py)
#
# Run AFTER python/analysis.py has created data/processed/employees_clean.csv
#   Rscript r/attrition_model.R        (from the project folder)
#
# NOTE: written to mirror the Python analysis, so you can compare results across both languages.
#       The Python version was run and verified; run this one yourself and check the output.
# =====================================================================
suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
})

dir.create("images", showWarnings = FALSE)
dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)

df <- read.csv("data/processed/employees_clean.csv", stringsAsFactors = TRUE)
df$left <- as.integer(df$attrition == "Yes")
df$overtime <- relevel(df$overtime, ref = "No")

# ---- 1. Hypothesis tests --------------------------------------------------
cat("\n--- Chi-square: attrition vs overtime ---\n")
print(chisq.test(table(df$overtime, df$attrition)))

cat("\n--- Wilcoxon (Mann-Whitney): income, leavers vs stayers ---\n")
print(wilcox.test(monthly_income ~ attrition, data = df))

# ---- 2. Logistic regression (interpretable odds ratios) --------------------
fit <- glm(
  left ~ overtime + job_satisfaction + work_life_balance + scale(monthly_income) +
         years_at_company + years_since_last_promotion + distance_from_home_km + department,
  data = df, family = binomial()
)
print(summary(fit))

or <- data.frame(
  term       = names(coef(fit)),
  odds_ratio = exp(coef(fit)),
  ci_low     = exp(confint.default(fit)[, 1]),
  ci_high    = exp(confint.default(fit)[, 2]),
  p_value    = summary(fit)$coefficients[, 4]
) %>% filter(term != "(Intercept)") %>% arrange(desc(odds_ratio))
write.csv(or, "data/processed/r_odds_ratios.csv", row.names = FALSE)
print(or, digits = 3)

# ---- 3. Odds-ratio forest plot ---------------------------------------------
p <- ggplot(or, aes(x = reorder(term, odds_ratio), y = odds_ratio)) +
  geom_pointrange(aes(ymin = ci_low, ymax = ci_high), colour = "#1f6feb") +
  geom_hline(yintercept = 1, linetype = "dashed", colour = "#d93025") +
  coord_flip() + scale_y_log10() +
  labs(title = "Odds ratios for leaving (95% CI, log scale)",
       x = NULL, y = "Odds ratio (>1 raises attrition risk)") +
  theme_minimal(base_size = 11)
ggsave("images/05_r_odds_ratios.png", p, width = 8, height = 4.5, dpi = 130)
cat("\nSaved images/05_r_odds_ratios.png and data/processed/r_odds_ratios.csv\n")
