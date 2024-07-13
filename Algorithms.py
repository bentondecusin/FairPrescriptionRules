import ast
import multiprocessing
import statistics
import Utils
import warnings
import Data2Transactions
import time
import logging
warnings.filterwarnings('ignore')
PATH = "./data/"
CPU_COUNT = 8

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

def filterPatterns(df, groupingAtt, groups):
    groups_dic = {}
    for group in groups:
        df['GROUP_MEMBER'] = df.apply(lambda row: isGroupMember(row, group), axis=1)
        df_g = df[df['GROUP_MEMBER'] == 1]
        covered = set(df_g[groupingAtt].tolist())
        groups_dic[str(group)] = frozenset(covered)
    from collections import defaultdict

    grouped = defaultdict(list)
    for key in groups_dic:
        grouped[groups_dic[key]].append(key)

    ans = []
    for k,v in grouped.items():
        if len(v) > 1:
            v = [ast.literal_eval(i) for i in v]
            ans.append(min(v, key=lambda x: len(x)))
        else:
            ans.append(ast.literal_eval(v[0]))
    return ans


def getAllGroups(df_org, atts, t):
    df = df_org.copy(deep=True)
    df = df[atts]
    df, rows, columns = Data2Transactions.removeHeader(df, 'Temp.csv')
    rules = Data2Transactions.getRules(df, rows, columns, min_support=t)
    return rules


def getGroupstreatmentsforGreeedy(DAG, df, groupingAtt, groups, ordinal_atts, targetClass,
                        high, low, actionable_atts, print_times, sample = False):
    manager = multiprocessing.Manager()
    groups_dic = manager.dict()
    elapsed_time = 0

    start_time = time.time()
    arg_list = [(group, df, groups_dic, groupingAtt, targetClass, DAG, ordinal_atts, high, low,
                 actionable_atts) for group in groups]
    # Create a non-daemonic process pool
    with multiprocessing.get_context('spawn').Pool() as pool:
        # Apply the update_dictionary function to each argument in parallel
        pool.starmap(process_group_greedy, arg_list)

    elapsed_time = time.time() - start_time

    if print_times:
        logging.info(f"Elapsed time step 2: {elapsed_time} seconds")
    return groups_dic, elapsed_time


def process_group_greedy(group, df, groups_dic, groupingAtt, targetClass,
                   DAG, ordinal_atts, high, low,
    actionable_atts):

    df['GROUP_MEMBER'] = df.apply(lambda row: isGroupMember(row, group), axis=1)
    df_g = df[df['GROUP_MEMBER'] == 1]
    drop_atts = list(group.keys())
    drop_atts.append('GROUP_MEMBER')
    drop_atts.append(groupingAtt)

    covered = set(df_g[groupingAtt].tolist())

    (t_h, cate_h) = getHighTreatments(df_g, group, targetClass,
                                      DAG, drop_atts,
                                      ordinal_atts, high, low, actionable_atts)

    groups_dic[str(group)] = [len(df_g), covered, t_h, cate_h]


def isGroupMember(row, group):
    for att in group:
        column_c_type = type(row[att])
        if type(row[att]) == int:
            if not row[att] == int(group[att]):
                return 0
        elif type(row[att]) == str:
            if row[att] == group[att]:
                return 1
            else:
                return 0
        elif int(row[att]) == int(group[att]):
                return 1
        elif not row[att] == group[att]:
            return 0
    return 1


def getHighTreatments(df_g, group, target, DAG, dropAtt, ordinal_atts, high, low, actionable_atts_org):
    df_g.drop(dropAtt, axis=1, inplace=True)
    actionable_atts = [a for a in actionable_atts_org if not a in dropAtt]
    df_g = df_g.loc[:, ~df_g.columns.str.contains('^Unnamed')]
    logging.info(f'Starting group: {group}')
    treatments = Utils.getLevel1treatments(actionable_atts, df_g, ordinal_atts)
    logging.info(f'Number of treatments at level I: {len(treatments)}')

    t_h = None
    cate_h = 0
    treatments_cate, t_h, cate_h = Utils.getCatesGreedy(DAG, t_h, cate_h, df_g, ordinal_atts, target, treatments)

    logging.debug(f"Debug - treatments_cate before filtering: {treatments_cate}")

    treatments_cate = filter_above_median(treatments_cate)

    treatments = Utils.getNextLeveltreatments(treatments_cate, df_g, ordinal_atts, high, False)
    logging.info(f'Number of treatments at level II: {len(treatments)}')
    treatments_cate, t_h2, cate_h2 = Utils.getCatesGreedy(DAG, t_h, cate_h, df_g, ordinal_atts, target, treatments)
    
    if t_h2 != t_h:
        logging.info("High treatment found in level 2")
        t_h = t_h2
        cate_h = cate_h2

    logging.info(f'Finished group: {group}')
    logging.info(f't_h: {t_h}, cate_h: {cate_h}')
    logging.info('#######################################')
    return (t_h, cate_h)


def filter_above_median(treatments_cate):
    positive_values = [value for value in treatments_cate.values() if value > 0]

    if not positive_values:
        return {}

    positive_median = statistics.median(positive_values)

    filtered = {treatment: value for treatment, value in treatments_cate.items()
                if value > positive_median}

    logging.debug(f"Filtered treatments_cate: {filtered}")

    return filtered
