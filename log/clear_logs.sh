for entry in /var/log/*-messages
do
  echo "" >  "$entry"
done
