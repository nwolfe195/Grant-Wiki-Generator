# Grant_Wiki_Generator

This script performs the automated retrieval of NIH RePORTER data containing grants for Brigham and Women's Hospital, from 2009 to current day.  A wiki page within chanmine will be created for each grant, as well as a page for each researcher linking to their grants.

To run the script, call the shell script grant_wiki_writer.sh, which should take care of everything else.  You will be prompted for your channing username and password.  

By default, the script writes pages to chanmine2.  To write to the main chanmine wiki, use the command
grant_wiki_writer.sh chanmine

Running the script will leave a log file.

Run time is approximately 1.5 hours.
