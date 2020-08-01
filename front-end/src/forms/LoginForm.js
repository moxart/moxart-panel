import React, { useState } from "react";
import { useHistory } from "react-router-dom";
import { useForm } from "react-hook-form";

const LoginForm = () => {
    const history = useHistory();
    const { register, handleSubmit, errors } = useForm();
    const [serverErrors, setServerErrors] = useState([]);

    const onSubmit = async (formData) => {
        setServerErrors([]);

        const  response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        console.log(data);
        history.push('/');
    }

    return (
        <div className="container">
            <div className="row">
                <div className="col-md-5 mx-auto">
                    <h1>Login</h1>
                    <form autoComplete={`off`} onSubmit={handleSubmit(onSubmit)}>
                        <div className="form-group">
                            <label htmlFor="username">Username</label>
                            <input
                                type="username"
                                className="form-control"
                                name="username"
                                ref={register({ required: true, minLength: 4 })}
                            />
                            {errors.username && errors.username.type === "required" && (
                                <p>username is required</p>
                            )}
                            {errors.username && errors.username.type === "minLength" && (
                                <p>username is required min length of 4</p>
                            )}
                        </div>
                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input type="password"
                                   className="form-control"
                                   name="password"
                                   ref={register({ required: true, minLength: 6 })}
                            />
                            {errors.password && errors.password.type === "required" && (
                                <p>password is required</p>
                            )}
                            {errors.password && errors.password.type === "minLength" && (
                                <p>password is required min length of 6</p>
                            )}
                        </div>

                        <input type="submit" className={`btn btn-primary`} value={`Login`} />
                    </form>
                </div>
            </div>
        </div>
    )
}

export default LoginForm;
