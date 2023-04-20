
source ./.bash-preexec.sh
   
preexec() {
   PID=`echo $$`
   CURR_SESSION=`cat ~/.dagknows/default/current_session`
   SESSION_FOLDER=~/.dagknows/default/sessions/${CURR_SESSION}
   MYPPID=`ps -o ppid= -p ${PID} | xargs`
   MYPCMD=`ps -o comm= -p ${MYPPID} | xargs`
   if [ -f ~/.dagknows/default/enable_recording ]; then
     if [[ $MYPCMD = "script" ]]
     then
         echo "PROMPT: " "'${(%%)PS1}'" " CMD: " $1  >> ${SESSION_FOLDER}/.commands
     else
         echo "Sorry, the recording is not on. Turning it on now. Please type your command again"
         #echo $1 > ${SESSION_FOLDER}/.leftover
         script -a -q -F ${SESSION_FOLDER}/.cliblob
     fi
   else
     echo "Recording Disabled"
   fi
}

precmd() {
   #print "Done executing $2"
   #dag export
   echo
}
