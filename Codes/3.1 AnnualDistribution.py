# Updated publication-quality script
# Fixes:
# - Integer year ticks
# - No overlapping legends
# - Same y-axis limits
# - Smaller titles
# - Lighter annual line
# - TRMM rolling mean + CI only
# - ISS annual series + trend only

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator
from scipy.stats import linregress

base_dir = r"D:\Articles\Working\India Lightning"
input_file = os.path.join(base_dir,"Excel Files","India_LIS_AllYears_State_Season.xlsx")
fig_dir = os.path.join(base_dir,"Figures")
excel_dir = os.path.join(base_dir,"Derived_Statistics")

os.makedirs(fig_dir,exist_ok=True)
os.makedirs(excel_dir,exist_ok=True)

df = pd.read_excel(input_file)
annual = df.groupby("Year").size().reset_index(name="Flash_Count")

trmm = annual[(annual.Year>=2000)&(annual.Year<=2014)].copy()
iss = annual[(annual.Year>=2018)&(annual.Year<=2022)].copy()

def rolling(df,window=3):
    d=df.copy()
    d["Mean"]=d["Flash_Count"].rolling(window,center=True,min_periods=1).mean()
    sd=d["Flash_Count"].rolling(window,center=True,min_periods=1).std().fillna(0)
    n=d["Flash_Count"].rolling(window,center=True,min_periods=1).count()
    d["CI"]=1.96*sd/np.sqrt(n)
    return d

trmm=rolling(trmm)

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11})

fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,8),sharey=True,gridspec_kw={"hspace":0.22})

# TRMM
r1=linregress(trmm.Year,trmm.Flash_Count)
ax1.plot(trmm.Year,trmm.Flash_Count,color="0.8",lw=1)
ax1.scatter(trmm.Year,trmm.Flash_Count,s=70,color="#1f77b4",edgecolors="white",zorder=3,label="Annual events")
ax1.fill_between(trmm.Year,trmm.Mean-trmm.CI,trmm.Mean+trmm.CI,color="#6baed6",alpha=0.20)
ax1.plot(trmm.Year,trmm.Mean,color="#08519c",lw=3,label="3-year rolling mean")
ax1.plot(trmm.Year,r1.intercept+r1.slope*trmm.Year,"--",color="black",lw=2,label="Linear trend")
ax1.text(0.98,0.94,f"R² = {r1.rvalue**2:.3f}\np = {r1.pvalue:.3f}",transform=ax1.transAxes,
         ha="right",va="top",bbox=dict(fc="white",ec="0.7"))
ax1.set_title("(a) TRMM-LIS (2000–2014)",fontsize=14,fontweight="bold")
ax1.set_ylabel("Lightning Events")
ax1.grid(alpha=0.25)
ax1.legend(loc="upper left",frameon=False,ncol=3,bbox_to_anchor=(0,1.0))
ax1.xaxis.set_major_locator(FixedLocator(np.arange(2000,2015)))
ax1.set_xticks(np.arange(2000,2015))
ax1.tick_params(axis="x",labelbottom=True)

# ISS
r2=linregress(iss.Year,iss.Flash_Count)
ax2.plot(iss.Year,iss.Flash_Count,color="0.8",lw=1)
ax2.scatter(iss.Year,iss.Flash_Count,s=70,color="#d62728",edgecolors="white",zorder=3,label="Annual events")
ax2.plot(iss.Year,r2.intercept+r2.slope*iss.Year,"--",color="black",lw=2,label="Linear trend")
ax2.text(0.98,0.94,f"R² = {r2.rvalue**2:.3f}\np = {r2.pvalue:.3f}",transform=ax2.transAxes,
         ha="right",va="top",bbox=dict(fc="white",ec="0.7"))
ax2.set_title("(b) ISS-LIS (2018–2022)",fontsize=14,fontweight="bold")
ax2.set_xlabel("Year")
ax2.set_ylabel("Lightning Events")
ax2.grid(alpha=0.25)
ax2.legend(loc="upper left",frameon=False,ncol=2,bbox_to_anchor=(0,1.0))
ax2.xaxis.set_major_locator(FixedLocator(np.arange(2018,2023)))
ax2.set_xticks(np.arange(2018,2023))
ax2.set_xticklabels([str(y) for y in range(2018,2023)])

ymin=min(annual.Flash_Count)*0.9
ymax=max(annual.Flash_Count)*1.08
ax1.set_ylim(ymin,ymax)

stats=pd.DataFrame({
"Dataset":["TRMM","ISS"],
"R2":[r1.rvalue**2,r2.rvalue**2],
"p_value":[r1.pvalue,r2.pvalue],
"Slope":[r1.slope,r2.slope]
})
stats.to_excel(os.path.join(excel_dir,"Regression_Statistics.xlsx"),index=False)

plt.savefig(os.path.join(fig_dir,"Fig1_Yearwise_TRMM_ISS_Publication_v2.tif"),dpi=600,bbox_inches="tight")
plt.savefig(os.path.join(fig_dir,"Fig1_Yearwise_TRMM_ISS_Publication_v2.png"),dpi=600,bbox_inches="tight")
plt.close()
print("Finished")