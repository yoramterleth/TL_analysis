%% script to get the velocities obtained from image processing 

%% 
close all
clearvars 
clc

%% derive all the files 
folderPaths = {'D:\JIRP\JIRP_TL\full_trial\output_lower_icefall\'};
  % 'D:\JIRP\JIRP_TL\full_trial\output\' } ; 
    
% 'D:\JIRP\JIRP_TL\TL_perm\EMTanalysis\output_part1\' ,
%     'D:\JIRP\JIRP_TL\TL_perm\EMTanalysis\output_part2_3\'} ; 

t_plot = [] ; 
speed = [] ; 
figure 
for p = 1 :length(folderPaths)

% select folder path 
folderPath = folderPaths{p} ; 
disp(folderPath)

% Get a list of all files in the folder
files = dir(fullfile(folderPath, '*.*'));


% Loop through each file in the folder
for i = 1:length(files)

    % Skip the '.' and '..' entries, which represent the current and parent directories
    if strcmp(files(i).name, '.') || strcmp(files(i).name, '..')
        continue;
    end

    filename = [folderPath, files(i).name ] ; 
   
    % adjust function depending on data format
    if p ==1 
    A = importfile_lower_icefall(filename) ; 
    else 
      A = importfile_fixed_master_img(filename) ; 
    end 

    T = get_date(filename) ; 

    if isnat(T.aquisitionTime(2))
        continue 
    end 
    
   
   split = T.aquisitionTime(2)-T.aquisitionTime(1) ; 
   time(i) =  T.aquisitionTime(2) - (split/2) ; 


    vels = A.vmd ; 
    vels(vels<0) = nan ; 
    vels(vels>10) = nan ; 
    histogram(vels,NumBins=20), hold on 
    mean_vel(i) = median(vels,'omitnan') ; 

    if std(vels,'omitnan') > 1.5
        mean_vel(i) = nan ; 
    end 

end 

% mean_vel(mean_vel>20) = nan ; 
[t_plot_cur, ind] = sort(time') ; 
mean_vel = mean_vel' ; 
speed_cur= mean_vel(ind) ; 

t_plot = [t_plot; t_plot_cur] ; 
try 
speed = [speed; speed_cur] ; 
catch 
 speed = [speed; speed_cur']   ;
end 
end 

%% 
figure
scatter(t_plot, speed,60,'filled',"MarkerEdgeColor",'k'), hold on 
%plot(t_plot, movmean(speed,10,'omitnan'))
% ylim([0,10])
dt = [datetime(2023,07,16):days(1):datetime(2023,07,30)] ; 
xticks(dt)
ylabel('average ice velocity (m/day)')

%% write to csv file 
% Combine datetime and numeric vectors into a table
dataTable = table(t_plot, speed, 'VariableNames', {'DateTime', 'mean_vel_md'});

% Save the table to a CSV file
csvFileName = [folderPaths{1},'LowerIcefallMeanVel.csv'];
writetable(dataTable, csvFileName);

disp(['Data has been written to ' csvFileName]);
