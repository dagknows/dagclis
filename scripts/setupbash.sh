
source ./.bash-preexec.sh

preexec() {
   echo "dolar3 = $0 $1 $2 $3 - $*"
}
   
preexec2() {
   PID=`echo $$`
   MYPPID=`ps -o ppid= -p ${PID} | xargs`
   MYPCMD=`ps -o comm= -p ${MYPPID} | xargs`
   if [[ $MYPCMD = "script" ]]
   then
       echo "PROMPT: " "'${(%%)PS1}'" " CMD: " $3  >> ~/.commands
   else
       echo "Sorry, the recording is not on. Turning it on now. Please type your command again"
       #echo $3 > ~/.leftover
       script -a -q -F .cliblob
   fi
}

precmd() {
   #print "Done executing $2"
   #dag export
   echo
}
