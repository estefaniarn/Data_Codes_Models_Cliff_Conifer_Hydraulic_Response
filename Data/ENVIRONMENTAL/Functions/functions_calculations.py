import pandas as pd 
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

######VPD#####
def vpd(hobow):
    hobow['VPD']=(0.6108*np.exp((17.27*hobow['Temp(C)'])/(237.3+hobow['Temp(C)'])))*(1-(hobow['RH']/100))
    hobow['slope']=(2503*np.exp((17.27*hobow['Temp(C)'])/(237.3+hobow['Temp(C)'])))/((237.3+hobow['Temp(C)'])**2) #equation (5)ASCE
    return hobow

#####POTENTIAL EVAPOTRANSPIRATION ####
#equation (1) ASCE 
#0.0036 is to get W/m2 to MJ/m2h
#units of PET mm/h
def pet(hobow): 
    hobow['NetRad(MJ/m2h)']=hobow['NetRad']*0.0036
    solar_constant=hobow['NetRad(MJ/m2h)'].values.copy()
    dummy=hobow['NetRad(MJ/m2h)'].values.copy()
    for i,nr in enumerate(hobow['NetRad(MJ/m2h)']):
        solar_constant[i]=nr*0.04 if nr != (0.2*0.0036) else nr*0.2 #eq 65a y 65b nightime is when NetRad is less than zero or zero in our case 
        dummy[i]=0.25 if nr != (0.2*0.0036) else 1.7 #denominator constant that changes during daytime and nightime Table1 ASCE 0.24 and 0.96 if short crop-grass 
    hobow['G']=solar_constant 
    hobow['Cd']=dummy
    z=1719 #m elevation of Wasootch (above sea level)
    P=101.3*(((293-0.0065*z)/293)**(5.26)) #atmospheric pressure (kPa) eq (6) ASCE
    psy=0.00665*P #psychrometric constant kPa/C
    Cn=66 #Table 1 ASCE
    hobow['PET']=((0.408*hobow['slope']*(hobow['NetRad(MJ/m2h)']-hobow['G']))+(psy*(Cn/(hobow['Temp(C)']+273))*(hobow['WS']*hobow['VPD'])))/(hobow['slope']+(psy*(1+hobow['Cd']*hobow['WS'])))
    return hobow