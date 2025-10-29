#to get relative velocity, only necessary to an approach similar to Hahm, Dralle. Used if you don't have swa values 

from sklearn import preprocessing


def eliminate_neg(sf):
    #sf=df.copy()
    #create an index for values less than -1, I don't think lower values are reasonable 
    indexNames = sf[ (sf['Sap velocity corr OUT (cm/h)'] <= -1)].index #&(sf['Sap velocity corr OUT (cm h-1)'] >= 100) #If we wanted to restrict high values, from lit nothing is greater than 20 cm/h
    #sf.drop(indexNames , inplace=True) #eliminate all rows that use the above condition
    nanval=float("NaN") #make NaNs a float to replace empty spaces and then drop the NANs with dropna
    sf.replace(indexNames,nanval,inplace=True)# ("",nanval,inplace=True)
    #for name in ['Sap velocity corr OUT (cm/h)','Sap velocity corr IN (cm/h)','Sap flow corr OUT (cm3/h)','Sap flow corr IN (cm3/h)']:
    #    sf[name]=sf[name].interpolate(option='polynomial') 
    return sf 



def norm_vel(df): 
    sf=df.copy()
    #DROP NANS IF WE'RE NORMALIZING
    sf.dropna(subset=['Sap velocity corr OUT (cm/h)','Sap velocity corr IN (cm/h)'], inplace=True)
    #To use the function minmaax, that normalizes values with ratio i need to get the values of the column as an array, hence ".values" and then reshape that array bc minmaxsc wont read it in the shape (1,)
    svo=sf['Sap velocity corr OUT (cm/h)'].values.reshape(-1, 1) #returns numpy array, -1 means unknown dimension and numpy will figure it out 
    svi=sf['Sap velocity corr IN (cm/h)'].values.reshape(-1, 1)

    scaler = preprocessing.MinMaxScaler() #define the function
    SapOut_scaled = scaler.fit_transform(svo)
    SapIn_scaled = scaler.fit_transform(svi)

    return SapOut_scaled,SapIn_scaled
