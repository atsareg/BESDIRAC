# -*- coding: utf-8 -*-

from DIRAC import gLogger, gConfig, S_OK, S_ERROR, Time
from DIRAC.Core.Base.DB import DB
from DIRAC.Core.Utilities.MySQL import _quotedList

# Some basic arguments will use namedtuple 
from collections import namedtuple
import datetime

TransRequestEntry = namedtuple('TransRequestEntry',
                              [#'id',
                               'username',
                               'dataset',
                               'srcSE',
                               'dstSE',
                               'protocol',
                               'submit_time',
                               'status',
                               ])
TransRequestEntryWithID = namedtuple('TransRequestEntryWithID',
                                      ('id',) + TransRequestEntry._fields)
TransFileListEntry = namedtuple('TransFileListEntry',
                                [#'id',
                                 'LFN',
                                 'trans_req_id',
                                 'start_time',
                                 'finish_time',
                                 'status',
                                 'error',
                                 ])
TransFileListEntryWithID = namedtuple('TransFileListEntryWithID',
                                      ('id',) + TransFileListEntry._fields)

DatasetEntry = namedtuple('DatasetEntry',
                          [#'id',
                            'name',
                            'username',
                            ])
DatasetEntryWithID = namedtuple('DatasetEntryWithID',
                                ('id',) + DatasetEntry._fields)
FilesInDatasetEntry = namedtuple('FilesInDatasetEntry',
                                [#'id',
                                  'LFN',
                                  'dataset_id',
                                  ])
FilesInDatasetEntryWithID = namedtuple('FilesInDatasetEntryWithID',
                                ('id',) + FilesInDatasetEntry._fields)


class TransferDB(DB):
  tables = dict(TransferRequest = "TransferRequest",
                TransferFileList = "TransferFileList",
                Dataset = "Dataset",
                FilesInDataSet = "FilesInDataSet")

  def __init__(self, dbname="TransferDB", 
                     fullname="Transfer/TransferDB",
                     maxQueueSize = 10):
    DB.__init__(self, dbname, fullname, maxQueueSize)


  """override the original getFields"""
  def getFields( self, tableName, outFields = None,
                 condDict = None, offset = None,
                 limit = False, conn = None,
                 older = None, newer = None,
                 timeStamp = None, orderAttribute = None,
                 greater = None, smaller = None ):
    """
      Select "outFields" from "tableName" with condDict
      N records can match the condition
      return S_OK( tuple(Field,Value) )
      if outFields == None all fields in "tableName" are returned
      if limit is not False, the given limit is set
      inValues are properly escaped using the _escape_string method, they can be single values or lists of values.
    """
    table = _quotedList( [tableName] )
    if not table:
      error = 'Invalid tableName argument'
      self.log.warn( 'getFields:', error )
      return S_ERROR( error )

    quotedOutFields = '*'
    if outFields:
      quotedOutFields = _quotedList( outFields )
      if quotedOutFields == None:
        error = 'Invalid outFields arguments'
        self.log.warn( 'getFields:', error )
        return S_ERROR( error )

    self.log.verbose( 'getFields:', 'selecting fields %s from table %s.' %
                          ( quotedOutFields, table ) )

    if condDict == None:
      condDict = {}

    try:
      condition = self.buildCondition( condDict = condDict, older = older, newer = newer,
                        timeStamp = timeStamp, orderAttribute = orderAttribute, limit = limit,
                        offset = offset,
                        greater = None, smaller = None )
    except Exception, x:
      return S_ERROR( x )

    return self._query( 'SELECT %s FROM %s %s' %
                        ( quotedOutFields, table, condition ), conn, debug = True )

  def insert_TransferRequest(self, entry):
    if not isinstance(entry, TransRequestEntry):
      raise TypeError("entry should be TransRequestEntry")
    infoDict = entry._asdict()
    res = self.insertFields( self.tables["TransferRequest"],
                             inDict = infoDict)
    if not res["OK"]:
      return res
    res = self._query("select last_insert_id()")
    if not res["OK"]:
      return res
    id = res['Value'][0][0]
    return S_OK(id)

  def get_TransferRequest(self, condDict = None):
    res = self.getFields( self.tables["TransferRequest"],
                          outFields = TransRequestEntryWithID._fields,
                          condDict = condDict,
                          )
    return res


  def get_TransferRequestTotal(self, condDict = None):
    res_total = self.countEntries(self.tables["TransferRequest"],
                                  condDict=condDict)
    return res_total

  def get_TransferRequestWithLimit(self, condDict=None, orderby=None, offset=None, limit=None):
    """
    >>> orderby = "id"
    or
    >>> orderby = ["id:DESC", "name:ASC"]

    >>> offset = 5 # begin
    >>> limit = 5 # total entries
    """
    res = self.getFields( self.tables["TransferRequest"],
                          outFields = TransRequestEntryWithID._fields,
                          condDict = condDict,
                          orderAttribute = orderby,
                          limit = limit,
                          offset = offset,
                          )
    return res

  def insert_PerTransferFile(self, entry):
    if not isinstance(entry, TransFileListEntry):
      raise TypeError("entry should be TransFileListEntry")
    infoDict = entry._asdict()
    res = self.insertFields( self.tables["TransferFileList"],
                             inDict = infoDict)
    if not res["OK"]:
      return res
    res = self._query("select last_insert_id()")
    return res

  def insert_TransferFileList(self, trans_req_id, filelist):
    # << get list of files for the dataset >>
    for dsfile in map(FilesInDatasetEntryWithID._make, filelist):
      entry = TransFileListEntry(LFN = dsfile.LFN,
                                 trans_req_id = trans_req_id,
                                 start_time = None,
                                 finish_time = None,
                                 status = "new",
                                 error = "",
                                 )
      self.insert_PerTransferFile(entry)

  def get_TransferFileList(self, condDict = None):
    res = self.getFields( self.tables["TransferFileList"], 
                           outFields = TransFileListEntryWithID._fields,
                           condDict = condDict,
                           )
    return res

  def insert_Dataset(self, dataset, user, filelist):
    # two step:
    # insert into Dataset table.
    # insert into Files in Dataset table.
    entry = DatasetEntry( name = dataset,
                          username = user,
                          )
    res = self.helper_insert_Dataset_table(entry)
    if not res["OK"]:
      return res
    dataset_id = res["Value"]

    for perfile in filelist:
      entry = FilesInDatasetEntry( dataset_id = dataset_id,
                                   LFN = perfile)
      res = self.helper_insert_FilesInDataset_table(entry)
      if not res["OK"]:
        return res
    return S_OK()

  def get_Dataset(self, condDict = None):
    res = self.get_DatasetInfo(condDict)
    if not res["OK"]:
      return res
    filelist = []
    for entry in map(DatasetEntryWithID._make, res["Value"]):
      res2 = self.get_FilesInDataset( {"dataset_id": entry.id } )
      if not res2:
        return res2
      filelist . extend ( res2["Value"] )
    print filelist
    return S_OK(filelist)

  def get_DatasetInfo(self, condDict = None):
    res = self.getFields( self.tables["Dataset"], 
                          outFields = DatasetEntryWithID._fields,
                          condDict = condDict,
                        )
    return res

  def get_FilesInDataset(self, condDict = None):
    res = self.getFields( self.tables["FilesInDataSet"],
                          outFields = FilesInDatasetEntryWithID._fields,
                          condDict = condDict,
                        )
    return res

  def helper_insert_Dataset_table(self, entry):
    if not isinstance(entry, DatasetEntry):
      raise TypeError("entry should be DatasetEntry")
    infoDict = entry._asdict()
    res = self.insertFields( self.tables["Dataset"],
                             inDict=infoDict,
                             )
    if not res["OK"]:
      return res
    res = self._query("select last_insert_id()")
    if not res["OK"]:
      return res
    id = res['Value'][0][0]
    return S_OK(id)

  def helper_insert_FilesInDataset_table(self, entry):
    if not isinstance(entry, FilesInDatasetEntry):
      raise TypeError("entry should be FilesInDatasetEntry")
    infoDict = entry._asdict()
    res = self.insertFields( self.tables["FilesInDataSet"],
                             inDict=infoDict,
                             )
    return res

if __name__ == "__main__":
  from DIRAC.Core.Base import Script
  Script.parseCommandLine( ignoreErrors = True )

  gDB = TransferDB()

  entry = TransRequestEntry(username = "lintao", 
                            dataset = "my-dataset",
                            srcSE = "IHEP-USER",
                            dstSE = "IHEPD-USER",
                            protocol = "DIRACDMS",
                            status = "new",
                            submit_time = datetime.datetime.utcnow())
  res = gDB.insert_TransferRequest(entry)
  trans_id = 1
  if res["OK"]:
    trans_id = res["Value"]
    print trans_id
  print gDB.get_TransferRequest()
  print gDB.get_TransferRequest(condDict = {"id":1})

  entry = TransFileListEntry(LFN = "/path/does/not/exist",
                             trans_req_id = trans_id,
                             start_time = None,
                             finish_time = None,
                             status = "new",
                             error = "",
                             )
  gDB.insert_PerTransferFile(entry)

  filelist = map(str, range(10))

  condDict = {'trans_req_id': trans_id}
  print gDB.get_TransferFileList(condDict)
  condDict = {'status': 'new'}
  print gDB.get_TransferFileList(condDict)

  gDB.insert_Dataset( "my-dataset", "lintao", filelist)

  condDict = {'name': 'my-dataset-2'}
  print gDB.get_DatasetInfo(condDict)
  condDict = {}
  res = gDB.get_Dataset(condDict)
  if res["OK"]:
    filelist = res["Value"]
    gDB.insert_TransferFileList(trans_id, filelist)
