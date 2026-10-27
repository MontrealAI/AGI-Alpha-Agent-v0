# Raudenbush, S. W., & Bryk, A. S. (1985). Empirical Bayes meta-analysis.
# Journal of Educational Statistics, 10(2), 75-98.

# Raudenbush, S. W. (1984). Magnitude of teacher expectancy effects on pupil
# IQ as a function of the credibility of expectancy induction: A synthesis of
# findings from 18 experiments. Journal of Educational Psychology, 76(1),
# 85-97.

suppressPackageStartupMessages(library(metafor, quietly=TRUE))

dat.raudenbush1985 <- read.table("data-raw/dat.raudenbush1985.txt", header=TRUE, stringsAsFactors=FALSE)
dat.raudenbush1985$sei <- NULL
dat.raudenbush1985 <- escalc(measure="SMD", yi=yi, vi=vi, ni=n1i+n2i, data=dat.raudenbush1985, digits=4)
save(dat.raudenbush1985, file="data/dat.raudenbush1985.rda")
