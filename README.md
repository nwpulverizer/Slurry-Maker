The fastHTML version of this is available at nwpulver.pythonanywhere.com 

The server is on a free tier so it is a little slow. Give it a second after you press calculate. To sign in just enter a username and password and it will create a user account for you. Absolutely do not reuse passwords on this website that you share with other websites. The security is fairly low. 


# Run locally 
To run locally you will need the following packages:
```txt
python-fasthtml
numpy
plotly
```
Then, in the src directory you can run 
```shell
uvicorn app:app --reload

```
The UI should open in a web browser. If not visit 127.0.0.1:8000 in your browser. 
The materials DB from the hosted versionwill not be loaded. To add your own materials, create an account named admin with a strong password and click the add materials button. 
## TODO
- [ ] Make requirements.txt or similar
