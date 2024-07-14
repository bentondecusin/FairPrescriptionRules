import ast
import statistics
import Utils
import warnings
import Data2Transactions
import time
import logging
warnings.filterwarnings('ignore')
PATH = "./data/"

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
    groups_dic = {}
    elapsed_time = 0

    start_time = time.time()
    for group in groups:
        process_group_greedy(group, df, groups_dic, groupingAtt, targetClass, DAG, ordinal_atts, actionable_atts)

    elapsed_time = time.time() - start_time

    if print_times:
        logging.info(f"Elapsed time step 2: {elapsed_time} seconds")
    return groups_dic, elapsed_time

def process_group_greedy(group, df, groups_dic, groupingAtt, targetClass,
                   DAG, ordinal_atts, actionable_atts):

    df['GROUP_MEMBER'] = df.apply(lambda row: isGroupMember(row, group), axis=1)
    df_g = df[df['GROUP_MEMBER'] == 1]
    drop_atts = list(group.keys())
    drop_atts.append('GROUP_MEMBER')
    drop_atts.append(groupingAtt)

    covered = set(df_g[groupingAtt].tolist())

    (t_h, cate_h) = getHighTreatments(df_g, group, targetClass,
                                      DAG, drop_atts,
                                      ordinal_atts, actionable_atts)

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

def getHighTreatments(df_g, group, target, DAG, dropAtt, ordinal_atts, actionable_atts_org):
    df_g.drop(dropAtt, axis=1, inplace=True)
    actionable_atts = [a for a in actionable_atts_org if not a in dropAtt]
    df_g = df_g.loc[:, ~df_g.columns.str.contains('^Unnamed')]
    logging.info(f'Starting group: {group}')

    def calculate_fairness_score(treatment, df_g, DAG, ordinal_atts, target):
        cate_all =  Utils.getTreatmentCATE(df_g, DAG, treatment, ordinal_atts, target)
        protected_group = df_g[df_g['Gender'] != 'Male']  # Assuming 'Gender' is the protected attribute
        cate_protected = Utils.getTreatmentCATE(protected_group, DAG, treatment, ordinal_atts, target)
        if cate_all == cate_protected:
            return cate_all
        return cate_all / abs(cate_all - cate_protected)

    max_score = float('-inf')
    best_treatment = None
    best_cate = 0

    for level in range(1, 6):  # Up to 5 treatment levels
        logging.info(f'Processing treatment level {level}')
        
        if level == 1:
            treatments = Utils.getLevel1treatments(actionable_atts, df_g, ordinal_atts)
        else:
            positive_treatments = [t for t in treatments if Utils.getTreatmentCATE(df_g, DAG, t, ordinal_atts, target) > 0]
            treatments = Utils.getNextLeveltreatments(positive_treatments, df_g, ordinal_atts, True, False, DAG, target)

        logging.info(f'Number of treatments at level {level}: {len(treatments)}')

        for treatment in treatments:
            fairness_score = calculate_fairness_score(treatment, df_g, DAG, ordinal_atts, target)
            cate = Utils.getTreatmentCATE(df_g, DAG, treatment, ordinal_atts, target)
            score = fairness_score

            if score > max_score and cate > 0:
                max_score = score
                best_treatment = treatment
                best_cate = cate

        if level > 1 and max_score <= prev_max_score:
            logging.info(f'Stopping at level {level} as no better treatment found')
            break

        prev_max_score = max_score

    logging.info(f'Finished group: {group}')
    logging.info(f'Best treatment: {best_treatment}, CATE: {best_cate}, Fairness Score: {max_score}')
    logging.info('#######################################')
    return (best_treatment, best_cate)

def filter_above_median(treatments_cate):
    positive_values = [value for value in treatments_cate.values() if value > 0]

    if not positive_values:
        return {}

    positive_median = statistics.median(positive_values)

    filtered = {treatment: value for treatment, value in treatments_cate.items()
                if value > positive_median}

    logging.debug(f"Filtered treatments_cate: {filtered}")

    return filtered
