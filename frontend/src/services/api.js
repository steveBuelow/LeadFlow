import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:5000", //  Flask backend
  withCredentials: true, // <- required for session cookies
});

export default API;