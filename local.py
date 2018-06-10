#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script includes the local computations for decentralized regression with
normal equation including decentralized statistic calculation
"""
import numpy as np
import pandas as pd
import regression as reg
import sys
import ujson as json
from parsers import fsl_parser
from local_ancillary import add_site_covariates
from local_ancillary import local_stats_to_dict_fsl, ignore_nans


def local_0(args):
    input_list = args["input"]
    lamb = input_list["lambda"]

    (X, y) = fsl_parser(args)

    computation_output_dict = {
        "output": {
            "computation_phase": "local_0"
        },
        "cache": {
            "covariates": X.to_json(orient='split'),
            "dependents": y.to_json(orient='split'),
            "lambda": lamb,
        },
    }

    return json.dumps(computation_output_dict)


def local_1(args):
    X = pd.read_json(args["cache"]["covariates"], orient='split')
    y = pd.read_json(args["cache"]["dependents"], orient='split')
    lamb = args["cache"]["lambda"]

    y_labels = list(y.columns)

    t = local_stats_to_dict_fsl(X, y)
    _, local_stats_list, meanY_vector, lenY_vector = t

    augmented_X = add_site_covariates(args, X)

    X_labels = list(augmented_X.columns)

    biased_X = augmented_X.values

    XtransposeX_local = np.matmul(np.matrix.transpose(biased_X), biased_X)
    Xtransposey_local = np.matmul(np.matrix.transpose(biased_X), y)

    output_dict = {
        "XtransposeX_local":
        XtransposeX_local.tolist(),
        "Xtransposey_local":
        pd.DataFrame(Xtransposey_local).to_json(orient='split'),
        "mean_y_local":
        meanY_vector,
        "count_local":
        lenY_vector,
        "local_stats_list":
        local_stats_list,
        "X_labels":
        X_labels,
        "y_labels":
        y_labels,
        "lambda":
        lamb,
        "computation_phase":
        "local_1",
    }

    cache_dict = {
        "covariates": augmented_X.to_json(orient='split'),
    }
    computation_output_dict = {
        "output": output_dict,
        "cache": cache_dict,
    }

    return json.dumps(computation_output_dict)


def local_2(args):
    """Computes the SSE_local, SST_local and varX_matrix_local
    Args:
        args (dictionary): {"input": {
                                "avg_beta_vector": ,
                                "mean_y_global": ,
                                "computation_phase":
                                },
                            "cache": {
                                "covariates": ,
                                "dependents": ,
                                "lambda": ,
                                "dof_local": ,
                                }
                            }
    Returns:
        computation_output (json): {"output": {
                                        "SSE_local": ,
                                        "SST_local": ,
                                        "varX_matrix_local": ,
                                        "computation_phase":
                                        }
                                    }
    Comments:
        After receiving  the mean_y_global, calculate the SSE_local,
        SST_local and varX_matrix_local
    """
    cache_list = args["cache"]
    input_list = args["input"]

    X = pd.read_json(cache_list["covariates"], orient='split')
    y = pd.read_json(cache_list["dependents"], orient='split')
    biased_X = np.array(X)

    avg_beta_vector = input_list["avg_beta_vector"]
    mean_y_global = input_list["mean_y_global"]

    SSE_local, SST_local, varX_matrix_local = [], [], []
    for index, column in enumerate(y.columns):
        curr_y = y[column]

        if not curr_y.isna().all():
            X_, y_ = ignore_nans(biased_X, curr_y)

            SSE_local.append(
                reg.sum_squared_error(X_, y_, np.array(avg_beta_vector[
                    index])))
            SST_local.append(
                np.sum(np.square(np.subtract(y_, mean_y_global[index]))))

            varX_matrix_local.append(np.dot(X_.T, X_).tolist())
        else:
            SSE_local.append([])
            SST_local.append([])
            varX_matrix_local.append([])

    computation_output = {
        "output": {
            "SSE_local": SSE_local,
            "SST_local": SST_local,
            "varX_matrix_local": varX_matrix_local,
            "computation_phase": 'local_2'
        },
        "cache": {}
    }

    return json.dumps(computation_output)


if __name__ == '__main__':

    parsed_args = json.loads(sys.stdin.read())
    phase_key = list(reg.list_recursive(parsed_args, 'computation_phase'))

    if not phase_key:
        computation_output = local_0(parsed_args)
        sys.stdout.write(computation_output)
    elif "remote_0" in phase_key:
        computation_output = local_1(parsed_args)
        sys.stdout.write(computation_output)
    elif "remote_1" in phase_key:
        computation_output = local_2(parsed_args)
        sys.stdout.write(computation_output)
    else:
        raise ValueError("Error occurred at Local")
