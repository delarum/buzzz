from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, json, re
from datetime import datetime
from functools import wraps
 
app = Flask(__name__)
app.secret_key = "buzzz-secret-key-2026"
 
DB_PATH = os.path.join("data", "buzzz.db")
os.makedirs("data", exist_ok=True)