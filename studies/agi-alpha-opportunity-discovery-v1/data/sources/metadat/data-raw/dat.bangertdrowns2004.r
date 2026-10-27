# Bangert-Drowns, R. L., Hurley, M. M., & Wilkinson, B. (2004). The effects of
# school-based writing-to-learn interventions on academic achievement: A
# meta-analysis. Review of Educational Research, 74(1), 29-58.

dat.bangertdrowns2004 <- read.table("data-raw/dat.bangertdrowns2004.txt", header=TRUE, stringsAsFactors=FALSE)
names(dat.bangertdrowns2004)[5] <- "Ni"
dat.bangertdrowns2004$ni <- dat.bangertdrowns2004$Ni
dat.bangertdrowns2004$Ni <- NULL
dat.bangertdrowns2004$yi <- round((1 - 3/(4*dat.bangertdrowns2004$ni - 9)) * dat.bangertdrowns2004$di, 2)
dat.bangertdrowns2004$vi <- round((8 + dat.bangertdrowns2004$yi^2) / (2*dat.bangertdrowns2004$ni), 3) # assumes that n1 = n2
dat.bangertdrowns2004$di <- NULL
attr(dat.bangertdrowns2004, "digits") <- 3
attr(dat.bangertdrowns2004, "yi.names") <- "yi"
attr(dat.bangertdrowns2004, "vi.names") <- "vi"
attr(dat.bangertdrowns2004$yi, "measure") <- "SMD"
attr(dat.bangertdrowns2004$yi, "ni") <- dat.bangertdrowns2004$ni
class(dat.bangertdrowns2004) <- c("escalc", "data.frame")
save(dat.bangertdrowns2004, file="data/dat.bangertdrowns2004.rda", ascii=FALSE)
