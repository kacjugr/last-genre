1. fetch Last.fm top tags, and add them as suggestions options for the genre recommendations input.
    a. maybe a better source than Last.fm, since their tags are not necessarily genres
    b. options for top genres based on overall/year/month?

X2. Add caching last.fm fetch of a user's top artists.
    a. localStorage vs cookies?
    b. it should have a detection mechanism for 'staleness'. something like having an expiration on the check, probably # of minutes/hours equal to the number of plays for the top artist, possibly incrementing if re-fetchs return the same ranked list, and resetting if it does not.

X3. Larger top artist fetch. default to 50?  not sure if this will improve the results from the Gemini prompt

4. Export Gemini recommendation reply to Spotify playlist.

5. host the page somewhere?