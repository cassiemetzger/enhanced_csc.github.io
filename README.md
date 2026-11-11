# Read me 

To launch the website for the first time (locally), run these commands: 
<div align="center">

```bash 
pip install flask gdown
```

</div>

You will also need numpy and astropy. I assume you already have those installed. 

Then, clone the repository with: 
<div align = "center">

```bash 
git clone https://github.com/cassiemetzger/enhanced_csc.github.io.git
```

</div>

Launch the website locally (if you do this, the local website will update with your changes!): 
<div align="center"> 

```bash 
python app.py
```

</div>

To visit the website, first go to <code>app.py</code> and scroll to where it says <code>if __name__ == "__main__":</code>. You should see a line that says: "</code>app.run(debug=True, port=[SOME NUMBER])</code>". That number is your <b>port</b> that you will launch the website from. I currently have it set to 5000. So, to launch the website from port 5000, I would type: 
<div align = "center">

```http://127.0.0.1:5000/```

</div>

As you make changes, you can refresh this local copy of the website to see what you've done! 

If you add any data that is over 100 MB, be sure to add the file to .gitignore as Github cannot store files over 100 MB and you will not be able to push your changes if you include too large of a file. 

Use the following to add your changes to the repository. 

<div align = "center">

``` bash git add . 

git commit -m "[your message]" 

git push origin main 
``` 

</div>

After a few moments, you should be able to see your changes deployed on the "real" website 